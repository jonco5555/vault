# How to Run Vault

This guide provides step-by-step instructions to set up and run the Vault system using Docker. The setup involves multiple services, including the Manager, Bootstrap, Share Servers, and Client.

## Installation
1. Clone the Vault repository:
   ```bash
   git clone https://github.com/jonco5555/vault.git
   cd vault
   ```

2. Install:

    === "uv"
        ```bash
        uv sync
        ```

    === "docker"
        ```bash
        docker build -t vault .
        ```

    === "docker-compose"
        ```bash
        docker-compose build
        ```

## Running the System
=== "uv"
    ```bash
    uv run vault --help
    ```

=== "docker"
    ```bash
    docker run vault vault --help
    ```

=== "docker-compose"
    ```bash
    docker-compose up
    ```

## Full Example
```bash
chmod +x ./run_test_case.sh
./run_test_case.sh
```

## Running Evaluation Example
```bash
uv run ./evaluation/run_evaluation.py
```
