# credo-api-tools

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Collection of tools for exporting and working with data collected by CREDO.

[https://api.credo.science](https://api.credo.science)

## Requirements
need a config file in your ~/.kube directory

## create a pod on nautilus NRP cluster with Qualcomm Cloud AI 100:

  `kubectl apply -f scripts_example/fl-deployment.yaml | cat`
  `kubectl get pods -n cblee-credo`
  `kubectl port-forward -n cblee-credo deployment/fl-training 8888:8888 | cat`

## Apply Federated Learning to Pre-classified images
[https://github.com/carlynlee/FLSim/blob/main/docs/tutorials/federated_learning_for_image_classification.ipynb](https://github.com/carlynlee/FLSim/blob/main/docs/tutorials/federated_learning_for_image_classification.ipynb)
