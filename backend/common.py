"""
This file owns import and embedding of complaints from any source into firestore

The pipeline is as follows:
Data sources => Transform in the script => Embed contents => Load into Firestore using a standardized format
A complaint is a JSON object with the following keys:
[collection: "complaints"]
{
  "id": integer, primary key
  "date_created": YYYY-MM-DD,
  "body": <text of the complaint>
  "embedding": <n-dimensional vector>,
  "cluster_label": integer (>=0),
  "cluster_prob": float (0<=x<=1)
}

A cluster object is a JSON object with the following keys:
[collection: "clusters"]
{
    "cluster_label": integer (>=0),
    "cluster_size": integer (>0),
    "cluster_title": text,
    "cluster_body": text
}

This object exists at the final state of the document's lifetime.

Use Google's firestore. The code is geared towards cloud, so do not run locally
There should be a singular "ingest_data" function that loads from ... and inserts into firestore.
On error raise ImportError
"""
import asyncio
import csv
import random
import time
from math import ceil
from datetime import date

from shared import db

from sklearn.cluster import HDBSCAN

from google import genai
from google.genai import errors
from agentplatform import Client
from google.genai import types
from google.cloud import firestore
from google.adk.agents import Agent
from google.adk.runners import Runner
from vertexai.agent_engines import AdkApp
from google.genai.types import EmbedContentConfig
from google.adk.sessions import VertexAiSessionService

print("Finished imports")

FIRESTORE_PROJECT = "recht-technisch"
LOCATION = "europe-west1"
AGENT_BUCKET_ID = "recht-technisch-agent-bucket"
FIRESTORE_DATABASE = "complaints"


def _embed_with_backoff(client: genai.Client, body: str):
    """Embed one complaint, retrying temporary rate-limit responses."""
    max_retries = 5

    for attempt in range(max_retries + 1):
        try:
            return client.models.embed_content(
                model="gemini-embedding-001",
                contents=body,
                # Dimensionality set arbitrarily
                config=EmbedContentConfig(task_type="CLUSTERING", output_dimensionality=384),
            )
        except errors.ClientError as exc:
            if exc.code != 429 or attempt == max_retries:
                raise

            # Full jitter avoids repeatedly retrying at the same instant.
            delay = random.uniform(0, 2 ** attempt)
            print(
                f"Embedding rate-limited; retrying in {delay:.1f}s "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(delay)
    raise ValueError("Failed to embed complaint")


def ingest_data() -> None:
    """Import the complaints into the Firestore"""
    genai_client = None

    try:
        # ADC automatically picks up the Cloud Run service account credentials.
        complaints = db.collection("complaints")
        clean_complaints = []

        with open("/Users/Misha/Documents/Dev/projects/playground/temp/prunned_complaints.csv") as f:
            raw_complaints = list(csv.DictReader(f))

        if not raw_complaints:
            return None

        genai_client = genai.Client(
            # "enterprise" means the Vertex AI / Google Cloud endpoint here;
            # it does not imply an enterprise subscription.
            enterprise=True,
            project="recht-technisch",
            location=LOCATION,
        )

        # gemini-embedding-001 is documented as accepting one input per
        # request on Vertex AI, so do not send the complaints as one batch.
        for complaint in raw_complaints:
            if not isinstance(complaint, dict):
                raise ValueError("Complaint must be an object")

            body = complaint.get("body")
            date_created = complaint.get("date_created")

            if not isinstance(body, str) or not body.strip():
                raise ValueError("Complaint body must be non-empty text")
            if not isinstance(date_created, str):
                raise ValueError("date_created must be a YYYY-MM-DD string")

            try:
                date_created = date.fromisoformat(date_created).isoformat()
            except ValueError as exc:
                raise ValueError("date_created must be a YYYY-MM-DD string") from exc

            response = _embed_with_backoff(genai_client, body.strip())
            if len(response.embeddings) != 1:
                raise ValueError(
                    "Expected exactly one embedding per complaint, "
                    f"received {len(response.embeddings)}"
                )
            values = response.embeddings[0].values

            if (not hasattr(values, "__iter__")) or (not all([isinstance(i, float) for i in values])):
                raise ValueError("Malformed embedding values")

            clean_complaints.append({"date_created": date_created, "body": body.strip(), "embedding": values})

        @firestore.transactional
        def write_complaints(transaction, items):
            latest = (
                complaints.order_by("id", direction=firestore.Query.DESCENDING)
                .limit(1)
                .stream(transaction=transaction)
            )
            max_id = max(
                (doc.to_dict()["id"] for doc in latest),
                default=0,
            )

            for complaint in items:
                max_id += 1
                transaction.set(
                    complaints.document(f"complaint_{max_id}"),
                    {
                        "id": max_id,
                        "date_created": complaint["date_created"],
                        "body": complaint["body"],
                        "embedding": complaint["embedding"],
                    },
                )

        # Firestore transactions support at most 500 writes.
        for start in range(0, len(clean_complaints), 400):
            write_complaints(
                db.transaction(), clean_complaints[start: start + 400]
            )

    finally:
        if genai_client is not None:
            genai_client.close()

    return None


def cluster_complaints(min_samples: int = 3, min_cluster_size: int = 10) -> None:
    """
    Query complaints stored in Firestore and insert labels to documents and clusters back into Firestore
    """
    try:
        complaints = db.collection("complaints")
        documents = list(complaints.select(["embedding"]).stream())

        # Cluster documents are a snapshot of the latest clustering run.
        # Remove the previous snapshot so clusters that disappear are not
        # retained in Firestore.
        old_clusters = list(db.collection("clusters").stream())
        batch = db.batch()
        for cluster_document in old_clusters:
            batch.delete(cluster_document.reference)
        batch.commit()

        embeddings = [document.get("embedding") for document in documents]
        print("Started cluster inference")
        model = HDBSCAN(min_samples=min_samples, min_cluster_size=min_cluster_size)
        results = model.fit(embeddings)
        print("Finished cluster inference")
        labels = [int(label) for label in results.labels_]
        probabilities = results.probabilities_

        for document, label, probability in zip(
                documents,
                labels,
                probabilities,
                strict=True,
        ):
            document.reference.update({
                "cluster_label": int(label),
                "cluster_prob": float(probability),
            })

        clusters = dict()
        for l in labels:
            # HDBSCAN uses -1 for noise; noise is not a complaint cluster.
            if l >= 0:
                clusters[l] = clusters.get(l, 0) + 1

        for label, count in clusters.items():
            db.collection("clusters").document(f"cluster_{label}").set({
                "cluster_label": label,
                "cluster_size": count,
            })
    finally:
        if db is not None:
            db.close()

    return None


def _init_agent() -> str:
    """Return the owned Agent Engine ID, creating it when necessary.

    The Agent Engine is shared by the semantic-average jobs, while this
    function owns its Firestore client so it can safely be called from any
    execution context.
    """
    project = FIRESTORE_PROJECT
    app_name = "complaint_cluster_compiler"

    print("Init the agent.")
    try:
        agent_document = db.collection("meta").document("agent")
        stored_agent = agent_document.get()
        if stored_agent.exists:
            print("Agent already exists, returning cache")
            return stored_agent.to_dict()["id"]

        staging_bucket = "gs://" + AGENT_BUCKET_ID
        if not staging_bucket:
            raise RuntimeError(
                f"{staging_bucket} must be set to an existing "
                "Cloud Storage bucket before creating an Agent Engine, for example "
                "gs://recht-technisch-agent-engine-staging."
            )

        agent = Agent(
            name=app_name,
            model="gemini-2.5-flash",
            instruction="You are a runtime for complaint-cluster summaries.",
        )
        print("Creating new agent engine.")
        remote_agent = Client(project=project, location=LOCATION).agent_engines.create(
            agent=AdkApp(agent=agent, app_name=app_name),
            config={
                "display_name": "Complaint cluster compiler",
                "staging_bucket": staging_bucket,
                "requirements": [
                    "google-cloud-aiplatform[agent_engines,adk]",
                    "google-adk",
                ],
            },
        )
        agent_engine_id = remote_agent.api_resource.name
        agent_document.set({"id": agent_engine_id})
        print("Agent engine ID created & saved successfully.")
        return agent_engine_id
    finally:
        db.close()


def compile_semantic_averages() -> None:
    """Generate and store a title and summary for every complaint cluster.

    The ADK agent writes through tools that capture their values in local
    state.  Consequently, conversational text (including a final answer from
    the model) can never accidentally become a cluster summary.
    """
    agent_engine_id = _init_agent()

    try:
        clusters = db.collection("clusters")
        complaints = db.collection("complaints")
        sessions = VertexAiSessionService(
            project="recht-technisch",
            location=LOCATION,
            agent_engine_id=agent_engine_id,
        )
        for cluster_document in clusters.stream():
            print(f"Compiling average for id - {cluster_document.to_dict()['cluster_label']}")
            label = cluster_document.to_dict()["cluster_label"]
            cluster_complaints = list(
                complaints.where("cluster_label", "==", label).stream()
            )

            sample_size = min(10, max(3, ceil(len(cluster_complaints) * 0.3)))
            sample = random.sample(cluster_complaints, sample_size)
            complaint_text = ("\n" + "=" * 30 + "\n").join(
                f"{document.to_dict().get('body', '').strip()}"
                for document in sample
            )
            prompt = (
                "Your task is to summarize these customer complaints. They are "
                "a representative sample of one calculated complaint cluster. "
                "Call insert_title with a title of at most 60 characters and "
                "insert_body with a summary of at most 120 characters. "
                "Call both tools, even if one has already been called.\n\n"
                f"Complaints:\n{complaint_text}"
            )

            def insert_title(title: str) -> dict[str, str]:
                """Store a cluster title, rejecting text over 60 characters."""
                if not isinstance(title, str):
                    raise ValueError("Title must be text")
                title = title.strip()
                if not title:
                    raise ValueError("Title must not be empty")
                if len(title) > 60:
                    raise ValueError("Title must be at most 60 characters")
                title_db = _firestore_client()
                try:
                    title_db.collection("clusters").document(
                        cluster_document.id
                    ).update({"cluster_title": title})
                finally:
                    title_db.close()
                return {"status": "title stored"}

            def insert_body(body: str) -> dict[str, str]:
                """Store a cluster summary, rejecting text over 120 characters."""
                if not isinstance(body, str):
                    raise ValueError("Body must be text")
                body = body.strip()
                if not body:
                    raise ValueError("Body must not be empty")
                if len(body) > 120:
                    raise ValueError("Body must be at most 120 characters")
                body_db = _firestore_client()
                try:
                    body_db.collection("clusters").document(
                        cluster_document.id
                    ).update({"cluster_body": body})
                finally:
                    body_db.close()
                return {"status": "body stored"}

            print("\tRunning the agent")
            agent = Agent(
                name="complaint_cluster_compiler",
                model="gemini-2.5-flash",
                instruction=(
                    "Summarize the supplied customer complaints. You must "
                    "call insert_title exactly once with a title of at most "
                    "60 characters and insert_body exactly once with a "
                    "summary of at most 120 characters. If a tool rejects "
                    "your input, retry it with a shorter valid value. Do "
                    "not provide a summary in conversational text; use the "
                    "tools."
                ),
                tools=[insert_title, insert_body],
            )
            app_name = "complaint_cluster_compiler"
            user_id = "semantic-average-job"
            # VertexAiSessionService exposes an async API.  Resolve the
            # coroutine before passing the concrete session ID to Runner.
            session = asyncio.run(
                sessions.create_session(app_name=app_name, user_id=user_id)
            )
            runner = Runner(
                agent=agent,
                app_name=app_name,
                session_service=sessions,
            )
            message = types.Content(role="user", parts=[types.Part(text=prompt)])
            # Iterating the event stream drives the complete agent run,
            # including its insert_title and insert_body tool calls. The
            # individual events are not otherwise needed by this job.
            for _event in runner.run(
                    user_id=user_id,
                    session_id=session.id,
                    new_message=message,
            ):
                pass

            # The tools perform the writes. This read only verifies that the
            # agent actually called both tools; no model text is persisted.
            stored_cluster = clusters.document(cluster_document.id).get().to_dict()
            if not stored_cluster.get("cluster_title") or not stored_cluster.get("cluster_body"):
                raise RuntimeError(f"Agent did not provide both fields for cluster {label}")
            print("\tSuccessfully finished agent task.")
    finally:
        pass

    return None


if __name__ == "__main__":
    # print("Started ingesting.")
    # ingest_data()
    # print("Finished ingesting successfully!")

    # print("Started clustering pipeline")
    # cluster_complaints(min_samples=3, min_cluster_size=10)
    # print("Finished clustering pipeline successfully!")

    print("Start pipeline to compile semantic average")
    compile_semantic_averages()
    print("Finished pipeline to compile semantic average successfully!")
