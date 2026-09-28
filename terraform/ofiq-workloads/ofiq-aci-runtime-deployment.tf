terraform {
  required_providers {
    azurerm = {
        source = "hashicorp/azurerm"
        version = "~>4.0" # try with that, revert to 3.0 if doesn't work
    }
    random = {
        source  = "hashicorp/random"
        version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {
    
  }
}

variable "storage-suffix" {
  type = string
  description = "random suffix used by storage architecture which is more persistant then container runtime"
  default = "chjamd"
}

# Random suffix generator for the aci and it's resources, as we are imporitng the ifrastructure for storage
resource "random_string" "runtime-random-suffix" {
  length  = 6
  special = false
  upper   = false
}

# variables to tweak later, basically omitting the compose file
variable "dataset-to-use" {
    type        = string
    default     = "HR_128_normalized" # just change the default if you have multiple things in the input volume laying around
    description = "Dataset directory which's identities are going to be accessed, have to be specfied if there's more then 1 dataset"
}

variable "docker-image" {
    type        = string
    default     = "mikalaytsepl/ofiq-multibase-build-recursive:1.3"
    description = "OFIQ image from my repository"
}

# just referencing an existing resource group as data 
data "azurerm_resource_group" "diploma-rg" {
    name = "diploma-rg"
}

# referencing a key vault and pulling a RO secret token from it for DockerHub
data "azurerm_key_vault" "diploma-key-vault" {
    name = "diploma-key-vault"
    resource_group_name = "diploma-rg"
}

data "azurerm_key_vault_secret" "dockersecret" {
    name = "dockerhub-ro"
    key_vault_id = data.azurerm_key_vault.diploma-key-vault.id
}

# importing already created storage account and shraes as data 
data "azurerm_storage_account" "ofiq-storage" {
  name = "ofiqstore${var.storage-suffix}"
  resource_group_name = "diploma-rg"
}

# importing shares from the storage account
data "azurerm_storage_share" "share-in" {
    name = "dataset-in-${var.storage-suffix}"
    storage_account_id = data.azurerm_storage_account.ofiq-storage.id
}

data "azurerm_storage_share" "share-out" {
    name = "dataset-out-${var.storage-suffix}"
    storage_account_id = data.azurerm_storage_account.ofiq-storage.id
}

# Create ACI container group and instance 
resource "azurerm_container_group" "ofiq-runner" {
    name                = "ofiq-container-runner-${random_string.runtime-random-suffix.result}"
    location            = data.azurerm_resource_group.diploma-rg.location
    resource_group_name = data.azurerm_resource_group.diploma-rg.name
    os_type             = "Linux"
    restart_policy      = "OnFailure"

    # This one doesn't have any ip endpoints poking out 
    ip_address_type = "None"

    # adding image registry credentials to not being blocked by dockerhub
    image_registry_credential {
        server = "index.docker.io"
        username = "mikalaytsepl"
        password = data.azurerm_key_vault_secret.dockersecret.value # referencing a secret
    }

    # actual conainer definitoin and specs
    container {
      name   = "ofiq-evaluator-${random_string.runtime-random-suffix.result}"
      image  = var.docker-image # refing the image defined at the top
      # Both in GB
      cpu    = "2.0"
      memory = "4.0"

      environment_variables = { 
          "DATASET_TO_USE" = var.dataset-to-use
      }

      # Input volume mount (Fixed internal path for script compatibility)
      volume {
          name                 = "input-volume"
          mount_path           = "/OFIQ-Project/dataset-in"
          storage_account_name = data.azurerm_storage_account.ofiq-storage.name
          storage_account_key  = data.azurerm_storage_account.ofiq-storage.primary_access_key
          share_name           = data.azurerm_storage_share.share-in.name
      }

      # Output volume mount (Fixed internal path for script compatibility)
      volume {
          name                 = "output-volume"
          mount_path           = "/OFIQ-Project/dataset-out"
          storage_account_name = data.azurerm_storage_account.ofiq-storage.name
          storage_account_key  = data.azurerm_storage_account.ofiq-storage.primary_access_key
          share_name           = data.azurerm_storage_share.share-out.name
      }
    }
}
