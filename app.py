from flask import Flask, render_template, request, redirect, url_for, flash
from db_config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import date, datetime
import calendar

app = Flask(__name__)
app.secret_key = "secret123"


# ================= HOME PAGE (MENU) =================
@app.route("/")
def home():
    return render_template("home.html")
@app.route("/index")
def index():
    return render_template("index.html")



@app.route("/admin_login", methods=["POST"])
def admin_login():
    username = request.form["username"]
    password = request.form["password"]

    # STATIC ADMIN CREDENTIALS
    if username == "admin" and password == "admin123":
        return redirect(url_for("index"))
    else:
        flash("Invalid admin credentials", "error")
        return redirect(url_for("home"))



@app.route("/tenant_login", methods=["POST"])
def tenant_login():
    name = request.form["name"]
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch tenant data from the database based on name
    cursor.execute("""
        SELECT id, password
        FROM tenant_det
        WHERE name = %s
    """, (name,))

    tenant = cursor.fetchone()
    conn.close()

    if tenant and check_password_hash(tenant["password"], password):  # Dehashing and checking password
        flash("Tenant login successful", "success")
        return redirect(url_for("tenant_requests", tenant_id=tenant["id"]))
    else:
        flash("Invalid tenant name or password", "error")
        return redirect(url_for("home"))

@app.route("/requests/<int:tenant_id>", methods=["GET", "POST"])
def tenant_requests(tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch tenant name & room
    cursor.execute("""
        SELECT name, roomno
        FROM tenant_det
        WHERE id = %s
    """, (tenant_id,))
    tenant = cursor.fetchone()

    if not tenant:
        conn.close()
        flash("Tenant not found", "error")
        return redirect(url_for("home"))

    if request.method == "POST":
        issue = request.form["issue"]

        cursor.execute("""
            INSERT INTO request_table (tenant_id, roomno, issue_description)
            VALUES (%s, %s, %s)
        """, (tenant_id, tenant["roomno"], issue))

        conn.commit()
        conn.close()

        flash("Request submitted successfully", "success")
        return redirect(url_for("tenant_requests", tenant_id=tenant_id))

    conn.close()
    return render_template("requests.html", tenant=tenant)
@app.route("/request", methods=["GET", "POST"])
def request_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        roomno = request.form["roomno"]
        issue = request.form["issue"]

        # 🔍 Get tenant_id from tenant name
        cursor.execute("""
            SELECT id FROM tenant_det WHERE name = %s
        """, (name,))
        tenant = cursor.fetchone()

        if not tenant:
            conn.close()
            flash("Tenant name not found", "error")
            return redirect(url_for("request_page"))

        tenant_id = tenant["id"]

        # ✅ Insert into request_table
        cursor.execute("""
            INSERT INTO request_table (tenant_id, roomno, issue_description)
            VALUES (%s, %s, %s)
        """, (tenant_id, roomno, issue))

        conn.commit()
        conn.close()

        flash("Request submitted successfully", "success")
        return redirect(url_for("request_page"))

    conn.close()
    return render_template("request.html")

@app.route("/create_password", methods=["GET", "POST"])
def create_password():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form["name"]
        password = request.form["password"]

        cursor.execute(
            "SELECT id FROM tenant_det WHERE name = %s",
            (name,)
        )
        tenant = cursor.fetchone()

        if tenant:
            hashed_password = generate_password_hash(password)

            cursor.execute(
                "UPDATE tenant_det SET password=%s WHERE name=%s",
                (hashed_password, name)
            )

            conn.commit()
            conn.close()
            flash("Password created successfully", "success")
            return redirect(url_for("home"))
        else:
            conn.close()
            flash("Tenant name not found", "error")  # Display error message

    conn.close()
    return render_template("create_password.html")



# ================= VIEW TENANT DETAILS =================
@app.route("/tenants")
def view_tenants():
    name = request.args.get("name")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if name:
        cursor.execute(
            "SELECT name, phone_number, roomno FROM tenant_det WHERE name LIKE %s",
            ('%' + name + '%',)
        )
    else:
        cursor.execute(
            "SELECT name, phone_number, roomno FROM tenant_det"
        )

    tenants = cursor.fetchall()
    conn.close()

    return render_template("view_details.html", tenants=tenants)



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




@app.route("/view_request", methods=["GET", "POST"])
def view_request():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        request_id = request.form["request_id"]
        new_status = request.form["status"]

        # Update the status of the request
        cursor.execute("""
            UPDATE request_table
            SET remark = %s
            WHERE request_id = %s
        """, (new_status, request_id))

        conn.commit()

    # Fetch all requests from the database
    cursor.execute("""
        SELECT 
            request_id,
            tenant_id,
            roomno,
            issue_description,
            remark
        FROM request_table
        ORDER BY request_id DESC
    """)
    requests = cursor.fetchall()
    conn.close()

    return render_template("view_request.html", requests=requests)



# ================= SHOW AVAILABLE ROOMS =================
@app.route("/rooms")
def show_rooms():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT roomno FROM room WHERE status = 'Available'")
    rooms = cursor.fetchall()
    conn.close()

    return render_template("rooms.html", rooms=rooms)



# ================= RENT DETAILS =================

@app.route("/rent", methods=["GET", "POST"])
def rent_details():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    today = date.today()

    if request.method == "POST":
        tenant_id = request.form["tenant_id"]
        amount = request.form["amount"]
        month = int(request.form["month"])
        year = int(request.form["year"])

        month_paid = date(year, month, 1)
        payment_date = date(year, month, 5)

        # 🔍 Check if tenant already has rent record
        cursor.execute(
            "SELECT tenant_id FROM rent_tracker WHERE tenant_id = %s",
            (tenant_id,)
        )
        exists = cursor.fetchone()

        if exists:
            # ✅ UPDATE
            cursor.execute("""
                UPDATE rent_tracker
                SET amount_paid = %s,
                    month_paid = %s,
                    payment_date = %s
                WHERE tenant_id = %s
            """, (amount, month_paid, payment_date, tenant_id))
        else:
            # ✅ INSERT
            cursor.execute("""
                INSERT INTO rent_tracker
                (tenant_id, amount_paid, month_paid, payment_date)
                VALUES (%s, %s, %s, %s)
            """, (tenant_id, amount, month_paid, payment_date))

        conn.commit()

    # ---------- FETCH LATEST RENT STATUS ----------
    cursor.execute("""
        SELECT 
            t.name,
            t.roomno,
            r.amount_paid,
            r.month_paid,
            r.payment_date
        FROM tenant_det t
        LEFT JOIN rent_tracker r ON t.id = r.tenant_id
    """)
    rents = cursor.fetchall()

    # ---------- MONTH-BASED STATUS ----------
    

    today = date.today()
    current_year = today.year
    current_month = today.month

    for r in rents:
        if r["month_paid"] is None:
            r["status"] = "DUE"
            continue

        paid_year = r["month_paid"].year
        paid_month = r["month_paid"].month

        # Convert months to comparable numbers
        paid_index = paid_year * 12 + paid_month
        current_index = current_year * 12 + current_month

        if paid_index >= current_index:
            r["status"] = "PAID"
        else:
            r["status"] = "DUE"


    # ---------- DROPDOWNS ----------
    cursor.execute("SELECT id, name FROM tenant_det")
    tenants = cursor.fetchall()

    months = [
        (1,"January"), (2,"February"), (3,"March"), (4,"April"),
        (5,"May"), (6,"June"), (7,"July"), (8,"August"),
        (9,"September"), (10,"October"), (11,"November"), (12,"December")
    ]

    years = list(range(today.year - 2, today.year + 3))

    conn.close()

    return render_template(
        "rent_details.html",
        rents=rents,
        tenants=tenants,
        months=months,
        years=years
    )





# ================= RUN APP =================
if __name__ == "__main__":
    app.run(debug=True)
