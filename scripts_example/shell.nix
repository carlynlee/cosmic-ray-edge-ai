{ pkgs ? import (builtins.fetchTarball {
  # This URL points to the exact commit e8c38b73aeb2 on NixOS/nixpkgs
  url = "https://github.com/NixOS/nixpkgs/archive/e8c38b73aeb2.tar.gz";
}) {} }:

pkgs.mkShell {
  buildInputs = [
    # Existing Python packages
    pkgs.python311
    pkgs.python311Packages.openai
    pkgs.python311Packages.numpy
    pkgs.python311Packages.pandas
    pkgs.python311Packages.matplotlib
    pkgs.python311Packages.pypdf2
    
    # Additional Python packages needed for ML and Kubernetes
    pkgs.python311Packages.pytorch
    pkgs.python311Packages.torchvision
    pkgs.python311Packages.kubernetes
    pkgs.python311Packages.jupyter
    pkgs.python311Packages.notebook
    pkgs.python311Packages.nbconvert
    
    # Kubernetes tools
    pkgs.kubectl
    pkgs.kubectx
    pkgs.kubernetes-helm
    
    # Development tools
    pkgs.cmake
    pkgs.vim
    pkgs.git
    pkgs.jq  # For JSON processing
    pkgs.yq  # For YAML processing
    
    # Docker tools (if needed for local testing)
    pkgs.docker
    pkgs.docker-compose
    
    # Additional utilities
    pkgs.curl
    pkgs.wget
    pkgs.openssh
  ];

  # Set environment variables
  shellHook = ''
    # Add any environment variables or shell setup here
    export PYTHONPATH="$PWD:$PYTHONPATH"
    
    # Optional: Set up kubectl configuration
    # export KUBECONFIG="$HOME/.kube/config"
    
    # Optional: Set up Python virtual environment
    # if [ ! -d "venv" ]; then
    #   python -m venv venv
    # fi
    # source venv/bin/activate
  '';
}
