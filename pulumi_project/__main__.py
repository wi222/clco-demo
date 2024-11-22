import os
import shutil
import pulumi
from pulumi_azure_native import resources, storage, web
from pulumi.asset import FileArchive

# 1. Ressourcengruppe erstellen
resource_group = resources.ResourceGroup("app-rg", location="westeurope")

# 2. Storage Account erstellen
storage_account = storage.StorageAccount(
    "appstorage",
    resource_group_name=resource_group.name,
    sku=storage.SkuArgs(name="Standard_LRS"),
    kind="StorageV2",
    allow_blob_public_access=True,
    location=resource_group.location,
)

# 3. Blob Container erstellen
blob_container = storage.BlobContainer(
    "app-container",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    public_access="Blob",
)

# 4. Dateien für die App vorbereiten
source_folder = os.path.abspath("..")  # Der Pfad zum Projekt-Root
temp_folder = os.path.abspath("temp_app")  # Temporärer Ordner für die ZIP-Vorbereitung

# Debugging: Pfade überprüfen
print(f"Source Folder: {source_folder}")
print(f"Temp Folder: {temp_folder}")

# Sicherstellen, dass der `source_folder` existiert
if not os.path.exists(source_folder):
    raise FileNotFoundError(f"Source folder '{source_folder}' does not exist. Please check the path.")

# Falls der temp_folder existiert, löschen und neu erstellen
if os.path.exists(temp_folder):
    shutil.rmtree(temp_folder)
os.makedirs(temp_folder, exist_ok=True)

# Kopiere Dateien ins temp-Verzeichnis
shutil.copytree(os.path.join(source_folder, "static"), os.path.join(temp_folder, "static"))
shutil.copytree(os.path.join(source_folder, "templates"), os.path.join(temp_folder, "templates"))
shutil.copy(os.path.join(source_folder, "requirements.txt"), os.path.join(temp_folder, "requirements.txt"))

# Verschiebe index.html ins Root des temp-Verzeichnisses
shutil.move(
    os.path.join(temp_folder, "templates", "index.html"),
    os.path.join(temp_folder, "index.html")
)

# Lösche den leeren "templates"-Ordner
shutil.rmtree(os.path.join(temp_folder, "templates"))

# Erstelle ein ZIP-Archiv
zip_path = "app.zip"
shutil.make_archive(base_name="app", format="zip", root_dir=temp_folder)

# Blob hochladen (App-Dateien)
blob = storage.Blob(
    "app-blob",
    resource_group_name=resource_group.name,
    account_name=storage_account.name,
    container_name=blob_container.name,
    source=FileArchive(zip_path),
)

# 5. App Service Plan erstellen
app_service_plan = web.AppServicePlan(
    "app-service-plan",
    resource_group_name=resource_group.name,
    sku=web.SkuDescriptionArgs(
        tier="Free",
        name="F1",
    ),
    location=resource_group.location,
)

# 6. Azure Web App erstellen
app = web.WebApp(
    "python-webapp",
    resource_group_name=resource_group.name,
    server_farm_id=app_service_plan.id,
    site_config=web.SiteConfigArgs(
        app_settings=[
            web.NameValuePairArgs(
                name="WEBSITE_RUN_FROM_PACKAGE",
                value=blob.url,
            )
        ]
    ),
    location=resource_group.location,
)

# 7. URL der Web-App als Output exportieren
pulumi.export("app_url", app.default_host_name.apply(lambda hostname: f"http://{hostname}"))
