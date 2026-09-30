terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40.0"
    }
  }
}

variable "project_id" {
  description = "Google Cloud Project ID for Siemens Knowledge Fabric"
  type        = string
}

variable "region" {
  description = "Primary GCP deployment region"
  type        = string
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Spanner Instance & Knowledge Fabric Graph Database
resource "google_spanner_instance" "knowledge_fabric_instance" {
  name         = "siemens-knowledge-fabric"
  config       = "regional-${var.region}"
  display_name = "Siemens Knowledge Fabric Graph Instance"
  processing_units = 100
}

resource "google_spanner_database" "code_graph_db" {
  instance = google_spanner_instance.knowledge_fabric_instance.name
  name     = "code-fabric-graph"
  ddl = [
    "CREATE TABLE Component (component_id STRING(64) NOT NULL, name STRING(128), file_path STRING(512)) PRIMARY KEY(component_id)",
    "CREATE TABLE DependencyEdge (component_id STRING(64) NOT NULL, dep_id STRING(64) NOT NULL, edge_type STRING(64)) PRIMARY KEY(component_id, dep_id), INTERLEAVE IN PARENT Component ON DELETE CASCADE",
    "CREATE OR REPLACE PROPERTY GRAPH SpannerCodeFabric NODE TABLES (Component) EDGE TABLES (DependencyEdge SOURCE KEY (component_id) REFERENCES Component (component_id) DESTINATION KEY (dep_id) REFERENCES Component (component_id))"
  ]
  deletion_protection = false
}

# 2. Secure Secret Manager for API & Enterprise Connectors
resource "google_secret_manager_secret" "jira_connector_token" {
  secret_id = "siemens-jira-connector-token"
  replication {
    auto {}
  }
}

# 3. Dedicated Least-Privilege Agent Service Account
resource "google_service_account" "agent_runtime_sa" {
  account_id   = "siemens-kf-agent-sa"
  display_name = "Siemens Knowledge Fabric ADK Runtime Service Account"
}

resource "google_project_iam_member" "spanner_user" {
  project = var.project_id
  role    = "roles/spanner.databaseUser"
  member  = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}

resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.agent_runtime_sa.email}"
}
