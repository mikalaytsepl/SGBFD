terraform{
    required_providers {
      azurerm = {
        source = "hashicorp/azurerm"
        version = "~>4.0"
      }
    }
}

provider "azurerm" {
  features {
    
  }
}

# variables 
variable "dataset_to_move" {
  default = ""
  type = string 
  description = "root name of the dataset which is going to be recursively moved to the google drive"
}


data "azurerm_resource_group" "diploma-rg" {
  name = "diploma-rg"
}

data "azurerm_storage_account" "fa-storage" {
    name = "ofiqstorechjamd"
    resource_group_name = data.azurerm_resource_group.diploma-rg.name
}

# container for the function app stuff to sit in
resource "azurerm_storage_container" "dataset-mover-container" {
  name = "dataset-mover-container"
  storage_account_id = data.azurerm_storage_account.fa-storage.id
  container_access_type = "private"
}

# Service plan for a consumption function app
resource "azurerm_service_plan" "flex_plan" {
  name                = "asp-flex"
  resource_group_name = data.azurerm_resource_group.diploma-rg.name
  location            = data.azurerm_resource_group.diploma-rg.location
  os_type             = "Linux" # Flex Consumption only supports Linux
  sku_name            = "FC1"   # SKU for Flex Consumption
}

resource "azurerm_function_app_flex_consumption" "dataset-mover" {
  name = "dataset-mover"
  resource_group_name = data.azurerm_resource_group.diploma-rg.name
  location = data.azurerm_resource_group.diploma-rg.location
  service_plan_id = azurerm_service_plan.flex_plan.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${data.azurerm_storage_account.fa-storage.primary_blob_endpoint}${azurerm_storage_container.dataset-mover-container.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = data.azurerm_storage_account.fa-storage.primary_access_key
  runtime_name                = "python"
  runtime_version             = "3.12"
  maximum_instance_count      = 100
  instance_memory_in_mb       = 512

  site_config {}
}