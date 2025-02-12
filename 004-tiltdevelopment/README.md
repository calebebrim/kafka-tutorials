# Accelerate Kubernetes Development with Tilt

As I was diving deeper into the Kafka universe, I came across a tool so useful that I had to take a step back and share it with you—**Tilt**! Whether you're working with Kubernetes-based applications or handling microservices, Tilt simplifies your local development workflow and makes it significantly more efficient.

When working on local development for Kubernetes-based applications, setting up a smooth, efficient, and automated workflow can be a challenge. Enter **Tilt**—a powerful tool that streamlines the process of developing microservices locally.

## 🚀 Why Use Tilt for Local Development?

Tilt provides a **fast, automated, and iterative** development experience for Kubernetes. Here’s why you should consider adding it to your workflow:

- **Live Updates** – Code changes are automatically detected and applied without needing to rebuild or redeploy the entire container.
- **Simplifies Workflows** – No need to manually run `kubectl` commands or apply YAML manifests repeatedly.
- **Integrated Logging & UI** – Get real-time feedback with an intuitive web UI and aggregated logs.
- **Works with Any Stack** – Tilt supports any language and framework, making it a universal development tool for Kubernetes.
- **Custom Dev Scripts** – Automate your local development process with customizable `Tiltfile` scripts.

## 🔥 Getting Started with Tilt and Kubernetes Using Kind

A great way to run a local Kubernetes cluster for development is **Kind** (Kubernetes in Docker). Here’s how you can quickly set up everything:

### 📌 Prerequisites

Make sure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Make](https://www.gnu.org/software/make/)

### ⚡ Setting Up Your Local Kubernetes Cluster with Kind

This tutorial was created inside **Windows WSL**, so if you are using a **Linux machine**, you should be able to follow along without any issues.

1. **Install Kind, Tilt, and Helm using Makefile:**

   ```sh
   make install-kind
   make install-tilt
   make install-helm
   ```

   This will install Kind, Tilt, and Helm on your machine automatically.

2. **Initialize the Docker Registry and Kubernetes Cluster:**

   ```sh
   make init-docker-repo
   make init-kind-cluster
   ```

   This sets up a local Docker registry and creates a Kubernetes cluster with Kind.

3. **Check if the Cluster is Running:**

   ```sh
   kubectl cluster-info --context kind-my-cluster
   ```

4. **Deploy a Sample Application (Optional):**

   ```sh
   kubectl apply -f https://k8s.io/examples/application/deployment.yaml
   ```

### 🚀 Setting Up Tilt

### 🛠️ Try Modifying the Python Code
Tilt enables live updates, so you can see changes reflected in real-time without needing to rebuild the entire container. Try editing `main.py` and change the response message in the `home` function:

```python
@app.route('/')
def home():
    return "Hello, Tilt! Kubernetes development just got easier!"
```

Once you save the file, Tilt will detect the changes and update the running container automatically. Refresh your browser at `http://localhost:8080` to see the new message instantly!

### 🐳 Understanding the Docker Image and Python Code

#### **Docker Image**
The `Dockerfile` used to build the containerized application should be structured efficiently to ensure smooth development and deployment. Here’s an example of how the Docker image is defined:

```Dockerfile
FROM python:3.12-alpine

WORKDIR /app

COPY main.py /app/
COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

EXPOSE 8080

CMD ["flask", "--app", "main.py", "--debug", "run", "--host=0.0.0.0", "--port=8080"]
```

#### **Python Application Code**
The application code is a simple Python service that runs inside the container:

```python
from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello Kubernetes World"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

1. **Initialize Tilt in Your Project:**
   Inside your project folder, create a `Tiltfile`:
   ```python
   docker_build(
       "hello-kubernetes",
       ".",
       dockerfile="Dockerfile",
       entrypoint=["flask", "--app", "main.py", "--debug", "run", "--host=0.0.0.0", "--port=8080"],
       live_update=[
           sync("src/", "/app/"),
           run("pip install -r requirements.txt", trigger="requirements.txt"),
       ]
   )

   helm_yaml = helm("helm/hello-kubernetes", name="hello-kubernetes")
   k8s_yaml(helm_yaml)

   k8s_resource("hello-kubernetes", port_forwards=8080)
   ```

### 📖 Explanation of the Tiltfile

#### **Docker Build with Live Update**

```python
   docker_build(
       "hello-kubernetes",
       ".",
       dockerfile="Dockerfile",
       live_update=[
           sync("src/", "/app/"),
           run("pip install -r requirements.txt", trigger="requirements.txt"),
       ]
   )
```

#### **Deploying Helm Chart**

```python
   helm_yaml = helm("helm/hello-kubernetes", name="hello-kubernetes")
   k8s_yaml(helm_yaml)
```

#### **Defining Kubernetes Resource and Port Forwarding**

```python
   k8s_resource("hello-kubernetes", port_forwards=8080)
```

### **Starting Tilt**

2. **Run the following command to start Tilt:**
   ```sh
   tilt up
   ```

🔗 Want to learn more? Check out the [Tilt documentation](https://docs.tilt.dev/) and [Kind documentation](https://kind.sigs.k8s.io/).

Happy coding! 🚀
