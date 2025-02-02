from flask import Blueprint, current_app, render_template

main_bp = Blueprint(name="main", import_name=__name__, template_folder="templates")


@main_bp.route("/index", methods=["GET"])
@main_bp.route("/", methods=["GET"])
def index():
    current_app.logger.debug("Loading home page...")
    return render_template(template_name_or_list="main/index.html")
