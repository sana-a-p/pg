from flask import Flask, render_template, request, redirect, url_for, flash
from db_config import get_db_connection

app = Flask(__name__)
app.secret_key = "secret123"


# ================= HOME PAGE (MENU) =================
@app.route("/")
def index():
    return render_template("index.html")


# ================= VIEW TENANT DETAILS =================
@app.route("/tenants")
def view_tenants():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT t.id, t.name, t.roomno, t.phone_number, r.status
        FROM tenant_det t
        JOIN room r ON t.roomno = r.roomno
        ORDER BY t.roomno
    """)
    tenants = cursor.fetchall()
    conn.close()

    return render_template("tenants.html", tenants=tenants)


# ================= REGISTER NEW TENANT =================
@app.route("/register", methods=["GET", "POST"])
def register_tenant():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        contact = request.form["contact"]
        roomno = request.form["roomno"]

        # 1️⃣ Check if room is still available
        cursor.execute(
            "SELECT status FROM room WHERE roomno = %s",
            (roomno,)
        )
        room = cursor.fetchone()

        if room and room["status"] == "Available":

            # 2️⃣ Insert tenant → tenant_id is auto-generated
            cursor.execute(
                """
                INSERT INTO tenant_det (name, roomno, phone_number)
                VALUES (%s, %s, %s)
                """,
                (name, roomno, contact)
            )

            tenant_id = cursor.lastrowid   # ✅ GENERATED TENANT ID

            # 3️⃣ Update room with tenant_id and status
            cursor.execute(
                """
                UPDATE room
                SET tenant_id = %s,
                    status = 'Occupied'
                WHERE roomno = %s
                """,
                (tenant_id, roomno)
            )

            conn.commit()
            conn.close()

            flash(f"Tenant registered successfully (ID: {tenant_id})", "success")
            return redirect(url_for("index"))

        else:
            flash("Selected room is not available", "error")

    # 4️⃣ GET request → show only available rooms
    cursor.execute(
        "SELECT roomno FROM room WHERE status = 'Available'"
    )
    rooms = cursor.fetchall()
    conn.close()

    return render_template("register.html", rooms=rooms)




# ================= ADD REQUEST / COMPLAINT =================
@app.route("/add_request", methods=["GET", "POST"])
def add_request():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        tenant_id = request.form["tenant_id"]
        roomno = request.form["roomno"]
        issue = request.form["issue"]

        cursor.execute("""
            INSERT INTO request_table (tenant_id, roomno, issue_description)
            VALUES (%s, %s, %s)
        """, (tenant_id, roomno, issue))

        conn.commit()
        conn.close()
        flash("Request added successfully", "success")
        return redirect(url_for("index"))

    cursor.execute("SELECT id, roomno FROM tenant_det")
    tenants = cursor.fetchall()
    conn.close()

    return render_template("add_request.html", tenants=tenants)


# ================= SHOW AVAILABLE ROOMS =================
@app.route("/rooms")
def show_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT roomno FROM room WHERE status = 'Available'")
    rooms = cursor.fetchall()
    conn.close()

    return render_template("rooms.html", rooms=rooms)


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(debug=True)
