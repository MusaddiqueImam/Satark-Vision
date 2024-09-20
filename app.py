from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import time


app = Flask(__name__)
app.secret_key = 'bd6361d5e217501e9773dca84e6518de'

# Maximum inactivity time in seconds (10 minutes)
MAX_INACTIVITY_TIME = 600

# Initialize the Firebase Admin SDK with your service account key
cred = credentials.Certificate("templates\satarkvision-firebase-adminsdk-b4kdf-8bc68b784b.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://satarkvision-default-rtdb.firebaseio.com/'
})

# Reference to your Firebase Realtime Database (users data node)
db_users = db.reference('users')
# Reference to your Firebase Realtime Database (companies data node)
db_companies = db.reference('companies')
# Reference to your Firebase Realtime Database (callers data node)
db_callers = db.reference('callers')

@app.route('/')
def home():
    animation_seen = session.get('animation_seen')

    # Check for a URL parameter to control the animation
    no_animation = request.args.get('animation') == 'false'

    if not animation_seen and not no_animation:
        session['animation_seen'] = True
        # Display the animation
        return render_template('animation.html')
    return render_template('index.html')

@app.route('/about-us')
def about_us():
    return render_template('about-us.html')

@app.route('/team')
def team():
    return render_template('team.html')

@app.route('/spam-call', methods=['GET', 'POST'])
def spamcall():
    if request.method == 'GET':
        return render_template('spam-call.html')

    if request.method == 'POST':
        phoneNo = request.form.get('phoneNo')  # Get the phone number from the form input field
    
        # Query the Firebase database based on phoneNo
        caller_data = db_callers.order_by_child('phoneNo').equal_to(phoneNo.lower()).get()

        if caller_data:
            # Get the first result (assuming phone numbers are unique)
            caller_id, data = next(iter(caller_data.items()))
            return render_template('spam-call.html', phoneNo=phoneNo, caller_data=caller_data)
        else:
            status = "Caller not found, may be this caller is a spammer."
            status_color = "text-gray-500"
            return render_template('spam-call.html', status=status, status_color=status_color, phoneNo=phoneNo)



@app.route('/fake-job', methods=['GET', 'POST'])
def fakejob():
    if request.method == 'GET':
        return render_template('fake-job.html')

    if request.method == 'POST':
        cmpny = request.form.get('cmpny')  # Get the company name or ID from the form input field

        # Query the Firebase database based on companyID
        query_id = db_companies.order_by_child('companyID').equal_to(cmpny.lower()).get()

        # Query the Firebase database based on companyName
        query_name = db_companies.order_by_child('companyName').equal_to(cmpny.lower()).get()

        type_mapping = {
            "gvt": "Government Organization",
            "pvt": "Private Organization",
            "mnc": "Multi-National Company",
            "none": "Not Found",
        }

        data = None  # Initialize data to None

        # Check if we found a result based on companyID
        if query_id:
            # Loop through the values of query_id
            for key, value in query_id.items():
                data = value
                break  # Break after getting the first result

        # If no result based on companyID, check if we found a result based on companyName
        if not data and query_name:
            # Loop through the values of query_name
            for key, value in query_name.items():
                data = value
                break  # Break after getting the first result

        if data:
            return render_template('fake-job.html', cmpny=cmpny, company=data, type_mapping=type_mapping)
        else:
            status = "Company not found, may be this company's job listing is fake."
            return render_template('fake-job.html', status=status, cmpny=cmpny)

    return render_template('fake-job.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'GET':
        return render_template('admin.html')
    
    if request.method == 'POST':
        userid = request.form.get('userid')
        query_user = db_users.order_by_child('userID').equal_to(userid.lower()).get()

        if query_user:
            password = request.form.get('password')
            data = next(iter(query_user.items()))[1]
            dbpassword = data.get('password')
            role = data.get('role')
            if password == dbpassword and role == 'administrator':
                session['user_info'] = {
                    'username': userid,
                    'role': role,
                    'authenticated': True,
                    'last_activity_time': time.time(),
                }
                session['dataInsertion'] = {
                    'callerData': True,
                    'callerMsg': '',
                    'companyData': True,
                    'companyMsg': '',
                }
                return redirect("/dashboard")
            else:
                if role != 'administrator':
                    return render_template('admin.html', status="Unauthenticated access is not allowed", status_color="text-red-500")
                return render_template('admin.html', status="Invalid userID or password", status_color="text-red-500")
        
        else:
            return render_template('admin.html', status="Invalid userID or password", status_color="text-red-500")


@app.route('/dashboard')
def admindash():
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    callerData = session.get('dataInsertion', {}).get('callerData', True)
    callerMsg = session.get('dataInsertion', {}).get('callerMsg', '')
    companyData = session.get('dataInsertion', {}).get('companyData', True)
    companyMsg = session.get('dataInsertion', {}).get('companyMsg', '')
    session['dataInsertion'] = {
        'callerData': True,
        'callerMsg': '',
        'companyData': True,
        'companyMsg': '',
    }
    return render_template('dashboard.html', callerData=callerData, callerMsg=callerMsg, companyData=companyData, companyMsg=companyMsg)

@app.route('/saveCaller', methods=['POST'])
def saveCaller():
    session['dataInsertion']['callerData'] = True
    callerName = request.form.get('callerName')
    phoneNo = request.form.get('phoneNo')
    caller_data = db_callers.order_by_child('phoneNo').equal_to(phoneNo.lower()).get()
    if caller_data:
        session['dataInsertion']['callerData'] = False
        session['dataInsertion']['callerMsg'] = 'This caller is already listed in the database'
        return redirect('/dashboard')
    else:
        db_callers.push({'callerName': callerName, 'phoneNo': phoneNo, 'isSpam': True})
        session['dataInsertion']['callerMsg'] = 'This caller has been successfully inserted in the database'
        return redirect('/dashboard')
    
@app.route('/saveCmpny', methods=['POST'])
def saveCmpny():
    session['dataInsertion']['companyData'] = True
    companyName = request.form.get('companyName')
    companyID = 'cpny2400' + request.form.get('companyID')
    companyType = request.form.get('companyType')
    rating = request.form.get('rating')
    company = db_companies.order_by_child('companyID').equal_to(companyID.lower()).get()
    if company:
        session['dataInsertion']['companyData'] = False
        session['dataInsertion']['companyMsg'] = 'This company already exist in the database'
        return redirect('/dashboard')
    else:
        db_companies.push({'companyName': companyName, 'companyID': companyID, 'type': companyType, 'isVerified': False, 'rating': rating})
        session['dataInsertion']['companyMsg'] = 'This company has been successfully inserted in the database'
        return redirect('/dashboard')
    
@app.route('/callerids')
def callerids():
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    data = db_callers.get()
    return render_template('caller-ids.html', data=data)

@app.route('/edit-caller/<caller_id>', methods=['GET', 'POST'])
def editcaller(caller_id):
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    caller = db_callers.child(caller_id).get()
    if request.method == 'POST':
        callerName = request.form.get('callerName')
        phoneNo = request.form.get('phoneNo')
        caller = db_callers.child(caller_id)
        caller.update({'callerName': callerName.lower(), 'phoneNo': phoneNo.lower()})
        return redirect('/callerids')
    return render_template('edit-caller.html', caller=caller, user_id=caller_id)

@app.route('/delete-caller/<caller_id>')
def deletecaller(caller_id):
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    caller = db_callers.child(caller_id)
    if caller.get():
        caller.delete()
    return redirect('/callerids')

@app.route('/toggle-spam/<caller_id>')
def toggle_spam(caller_id):
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    caller = db_callers.child(caller_id)
    if caller.get():
        getCaller = caller.get()
        getSpam = getCaller['isSpam']
        caller.update({'isSpam': not getSpam})
    return redirect('/callerids')

@app.route('/companies')
def companies():
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    data = db_companies.get()
    return render_template('companies.html', data=data)

@app.route('/edit-company/<company_id>', methods=['GET', 'POST'])
def editcompany(company_id):
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    company = db_companies.child(company_id)
    if request.method == 'POST' and company.get():
        companyName = request.form.get('companyName')
        companyID = request.form.get('companyID')
        companyType = request.form.get('companyType')
        rating = request.form.get('rating')
        company.update({
            "companyName": companyName.lower(),
            "companyID": companyID.lower(),
            "type": companyType,
            "rating": rating
        })
        print(companyName, companyID, companyType, rating)
        return redirect('/companies')
    company = db_companies.child(company_id).get()
    return render_template('edit-company.html', company=company, company_id=company_id)

@app.route('/toggle-verify/<company_id>')
def toggle_verify(company_id):
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    company = db_companies.child(company_id)
    if company.get():
        getCompany = company.get()
        getVerified = getCompany['isVerified']
        company.update({'isVerified': not getVerified})
    return redirect('/companies')

@app.route('/delete-company/<company_id>')
def deletecmpny(company_id):
    if not session.get('user_info', {}).get('authenticated', False):
        return redirect("/admin")
    current_time = time.time()
    if current_time - session.get('user_info', {}).get('last_activity_time', 0) > MAX_INACTIVITY_TIME:
        return redirect('/logout')
    company = db_companies.child(company_id)
    if company.get():
        company.delete()
    return redirect('/companies')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)