
  # Vibrant Customer Complaints Dashboard

  This is a code bundle for Vibrant Customer Complaints Dashboard. The original project is available at https://www.figma.com/design/R8gzRfZhQCF3wM71lzkybq/Vibrant-Customer-Complaints-Dashboard.

  ## Running the code

  Run `npm i` to install the dependencies.

  Run `npm run dev` to start the development server.

  ## Running the production container locally

  Docker Desktop does not reliably expose ports from `--network host` to
  macOS. Publish the frontend port explicitly instead:

  ```sh
  docker build -t complaints-dashboard . && \
    docker run --rm -p 3000:3000 \
      -v ~/.config/gcloud:/root/.config/gcloud:ro \
      complaints-dashboard
  ```

  Then open http://localhost:3000. The command intentionally continues
  running while it serves the application; stop it with `Ctrl+C`.
