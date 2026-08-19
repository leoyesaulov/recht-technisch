# This file explains TODOs and their status

* Write frontend (done - get from Figma)
* Decide which clusters to acutally use (done)
* Add footnote

Dev TODO:
**Michael**
* Have data a ingestion pipeline (owns ingestion, returns standardized set)
* Store data in Firestore (metadata-rich JSON Storage)
* Decide on embedding model (google's gemine embedding model)
* Decide where to store the vectors (Firestore)
* Decide the clustering model 
  (sklearn - HDBSCAN, hyperparams: high min samples to locate common complaints more aggressivery, middle min cluster size to prevent clusters from exploding)
* Store clusters in Firestore 
* Pull randomly 10% or 10 complaints from each cluster
* Have an agent take a sematic average (tool call) and the title (tool call)

**Leo**
* Google trigger to prevent rebuilding image

