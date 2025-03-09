import os
import sass
from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class AppsettingsConfig(AppConfig):
    name = "appsettings"

    def ready(self):
        """Recompile the theme on startup."""
        from django.conf import settings
        from django.core.management import call_command

        try:
            from appsettings.models import AppSettings

            # Ensure database is available before querying
            if "appsettings" in settings.INSTALLED_APPS:
                sass_dir = AppSettings.objects.get(key="SASS_DIR").value
                theme = AppSettings.objects.get(key="BOOTSTRAP_THEME").value
                main_css = os.path.join(settings.BASE_DIR, "static/css/wvc-main.min.css")

                scss_var = f"@import '{sass_dir}/wvc-themes/{theme}/variables';"
                scss_boot = f"@import '{sass_dir}/bootstrap-overrides.scss';"
                scss_bootswatch = f"@import '{sass_dir}/wvc-themes/{theme}/bootswatch';"

                css_compressed = sass.compile(
                    string=scss_var + "\n" + scss_boot + "\n" + scss_bootswatch,
                    output_style="compressed",
                )
                with open(main_css, "w") as css:
                    css.write(css_compressed)

                print(f"✔ Theme '{theme}' successfully recompiled at startup.")

        except (OperationalError, ProgrammingError):
            # Database isn't ready yet (e.g., during initial migrations)
            print("⚠ Database not ready. Skipping theme compilation.")
