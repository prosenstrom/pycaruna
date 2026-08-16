# GitHub settings for prosenstrom/pycaruna.
# Auth: export GITHUB_TOKEN with repo admin (gh auth token).
# First apply imports the live repo via imports.tf.
#
# Dependabot version updates on this fork are a one-time UI opt-in
# (see repository.tf). Alerts and security updates are managed here.

terraform {
  required_version = ">= 1.8.0"

  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.13"
    }
  }
}

provider "github" {
  owner = "prosenstrom"
}
