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

# Random suffix generator for each resource in order not to wait with hardcoded names
resource "random_string" "rand-suffix" {
  length  = 6
  special = false
  upper   = false
}

# just referencing an existing resource group as data 
data "azurerm_resource_group" "diploma-rg" {
    name = "diploma-rg"
}

# create a new storage account for shares to be in
resource "azurerm_storage_account" "ofiq-storage" {
    # lowercase and numbers only, this thing is PICKY
    name                     = "ofiqstore${random_string.rand-suffix.result}"
    resource_group_name      = data.azurerm_resource_group.diploma-rg.name
    location                 = data.azurerm_resource_group.diploma-rg.location
    account_tier             = "Standard"
    account_replication_type = "LRS"

    # prevents deletion of the whole storage account 
    lifecycle {
      prevent_destroy = true
    }
}

# create 2 10 gb shares
resource "azurerm_storage_share" "share-in" {
    name               = "dataset-in-${random_string.rand-suffix.result}"
    storage_account_id = azurerm_storage_account.ofiq-storage.id # apparently ref by name is deprecated
    quota              = 10 # size in GB

    # prevents input share from being deleted
    lifecycle {
      prevent_destroy = true
    }
}

resource "azurerm_storage_share" "share-out" {
    name               = "dataset-out-${random_string.rand-suffix.result}"
    storage_account_id = azurerm_storage_account.ofiq-storage.id # apparently ref by name is deprecated
    quota              = 10 # size in GB

    # prevents accidental deletion of the output share and results
    lifecycle {
      prevent_destroy = true
    }
}


# this will show nice outputs later on when resources are created so i would be able to reference them easily
output "storage_account_name" {
  value       = azurerm_storage_account.ofiq-storage.name
  description = "Persistent Storage Account Name"
}

output "share_in_name" {
  value       = azurerm_storage_share.share-in.name
  description = "Persistent Input Share Name"
}

output "share_out_name" {
  value       = azurerm_storage_share.share-out.name
  description = "Persistent Output Share Name"
}