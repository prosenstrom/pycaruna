resource "github_issue_label" "dependencies" {
  repository  = github_repository.pycaruna.name
  name        = "dependencies"
  color       = "0366d6"
  description = "Dependabot and dependency updates"
}
