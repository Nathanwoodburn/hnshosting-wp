from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory
import dotenv
import os
import requests
import stripe # For stripe payments
import smtplib, ssl # For sending emails

dotenv.load_dotenv()


app = Flask(__name__)

logins = []

# API add license key (requires API key in header)
@app.route('/add-licence', methods=['POST'])
def add_license():
    # Get API header
    api_key = request.headers.get('key')
    if api_key != os.getenv('LICENCE_KEY'):
        return jsonify({'error': 'Invalid API key', 'success': 'false'})

    # Generate licence key
    licence_key = os.urandom(16).hex()

    # Add license key to file
    key_file = open('/data/licence_key.txt', 'a')
    key_file.write(licence_key + '\n')
    key_file.close()

    return jsonify({'success': "true", 'licence_key': licence_key})


@app.route('/new-site', methods=['POST'])
def new_site():
    domain=request.args.get('domain')
    # Get API header
    api_key = request.headers.get('key')
    
    # Verify both API key and domain exist
    if api_key == None:
        return jsonify({'error': 'No licence provided', 'success': 'false'})
    
    if domain == None:
        return jsonify({'error': 'Missing domain', 'success': 'false'})

    # Check if API key is a valid site key
    key_file = open('/data/licence_key.txt', 'r')
    valid_key = False
    for line in key_file.readlines():
        if api_key == line.strip('\n'):
            valid_key = True
            break
    key_file.close()
    if not valid_key:
        return jsonify({'error': 'Invalid licence', 'success': 'false'})
    
    
    # Check if domain already exists
    if site_exists(domain):
        return jsonify({'error': 'Domain already exists', 'success': 'false'})
    
    # Check if domain contains http:// or https://
    if domain.startswith("http://") or domain.startswith("https://"):
        return jsonify({'error': 'Domain should not contain http:// or https://', 'success': 'false'})
    

    # Check if worker file exists
    workers = None
    try:
        worker_file = open('/data/workers.txt', 'r')
        workers = worker_file.readlines()
        worker_file.close()
    except FileNotFoundError:
        return jsonify({'error': 'No workers available', 'success': 'false'})
    
    # Get a worker that has available slots
    worker = None
    for line in workers:
        if not line.__contains__(':'):
            continue

        ip = line.split(':')[1].strip('\n')
        resp=requests.get("http://"+ip + ":5000/status",timeout=2)
        if (resp.status_code == 200):
            if resp.json()['availability'] == True:
                worker = line
                break
    
    if worker == None:
        return jsonify({'error': 'No workers available', 'success': 'false'})


    # Add domain to file
    sites_file = open('/data/sites.txt', 'a')
    sites_file.write(domain + ':' + worker.split(':')[0] + '\n')
    sites_file.close()

    # Use key
    key_file = open('/data/licence_key.txt', 'r')
    lines = key_file.readlines()
    key_file.close()
    key_file = open('/data/licence_key.txt', 'w')
    for line in lines:
        if line.strip("\n") != api_key:
            key_file.write(line)
    key_file.close()

    # Send worker request
    requests.post("http://"+ worker.split(':')[1].strip('\n') + ":5000/new-site?domain=" + domain)


    return jsonify({'success': 'true', 'domain': domain, 'status': "creating"})

# Add worker
@app.route('/add-worker', methods=['POST'])
def add_worker():
    worker=request.args.get('worker')
    worker_IP=request.args.get('ip')
    worker_PRIV=request.args.get('priv')
    # Get API header
    api_key = request.headers.get('key')
    if api_key == None or worker == None or worker_IP == None or worker_PRIV == None:
        return jsonify({'error': 'Invalid API key or worker info', 'success': 'false'})
    if api_key != os.getenv('WORKER_KEY'):
        return jsonify({'error': 'Invalid API key', 'success': 'false'})
    
    # Check worker file
    try:
        workers_file = open('/data/workers.txt', 'r')
    except FileNotFoundError:
        workers_file = open('/data/workers.txt', 'w')
        workers_file.close()
        workers_file = open('/data/workers.txt', 'r')
    
    # Check if worker already exists
    if worker in workers_file.read():
        return jsonify({'error': 'Worker already exists', 'success': 'false'})
    
    workers_file.close()

    # Add worker to file
    workers_file = open('/data/workers.txt', 'a')
    workers_file.write(worker + ":" + worker_PRIV + ":"+ worker_IP + '\n')
    workers_file.close()

    online=True
    resp=requests.get("http://"+worker_PRIV + ":5000/ping",timeout=2)
    if (resp.status_code != 200):
        online=False

    return jsonify({'success': 'true', 'worker': worker, 'online': online})

@app.route('/list-workers', methods=['GET'])
def list_workers():
    # Get API header
    api_key = request.headers.get('key')
    if api_key == None:
        return jsonify({'error': 'Invalid API key', 'success': 'false'})
    if api_key != os.getenv('WORKER_KEY'):
        return jsonify({'error': 'Invalid API key', 'success': 'false'})
    
    # Check worker file
    try:
        workers_file = open('/data/workers.txt', 'r')
    except FileNotFoundError:
        workers_file = open('/data/workers.txt', 'w')
        workers_file.close()
        workers_file = open('/data/workers.txt', 'r')
    
    workers = workers_file.readlines()
    workers_file.close()

    # Check if there are any workers (by seeing if there are any :)
    if len(workers) == 0:
        return jsonify({'error': 'No workers available', 'success': 'false'})

    worker_list = []
    for worker in workers:
        # Check worker status
        if not worker.__contains__(':'):
            continue

        online=True
        try:
            resp=requests.get("http://"+worker.split(':')[1].strip('\n') + ":5000/status",timeout=2)

            if (resp.status_code != 200):
                online=False
                worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[2].strip('\n'), 'online': online, 'sites': 0, 'status': 'offline'})
                continue
            sites = resp.json()['num_sites']
            availability = resp.json()['availability']
            if availability == True:
                worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[2].strip('\n'), 'online': online, 'sites': sites, 'status': 'ready'})
            else:
                worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[2].strip('\n'), 'online': online, 'sites': sites, 'status': 'full'})
        except:
            worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[2].strip('\n'), 'online': 'False', 'sites': 0, 'status': 'offline'})
            continue

    if len(worker_list) == 0:
        return jsonify({'error': 'No workers available', 'success': 'false'})
    return jsonify({'success': 'true', 'workers': worker_list})

@app.route('/site-info', methods=['GET'])
def site_status():
    domain = request.args.get('domain')
    domain = domain.lower()
    if domain == None:
        return jsonify({'error': 'Invalid domain', 'success': 'false'})
    
    # Check if domain exists
    if not site_exists(domain):
        return jsonify({'error': 'Domain does not exist', 'success': 'false'})
    
    # Get worker
    worker = site_worker(domain)
    if worker == None:
        return jsonify({'error': 'Domain does not exist', 'success': 'false'})
    
    # Get worker ip
    ip = workerIP_PRIV(worker)

    # Get TLSA record
    resp=requests.get("http://"+ip + ":5000/tlsa?domain=" + domain,timeout=2)
    json = resp.json()
    publicIP = workerIP(worker)

    if "tlsa" in json:
        tlsa = json['tlsa']
        return jsonify({'success': 'true', 'domain': domain, 'ip': publicIP, 'tlsa': tlsa})
    else:
        return jsonify({'success': 'false', 'domain': domain, 'ip': publicIP, 'tlsa': 'none','error': 'No TLSA record found'})


@app.route('/info')
def site_status_human():
    domain = request.args.get('domain')
    domain = domain.lower()
    if domain == None:
        return "<h1>Invalid domain</h1>"
    
    # Check if domain exists
    if not site_exists(domain):
        return "<h1>Domain does not exist</h1>"
    
    # Get worker
    worker = site_worker(domain)
    if worker == None:
        return "<h1>Domain does not exist</h1>"
    
    # Get worker ip
    ip = workerIP_PRIV(worker)

    # Get TLSA record    
    resp=requests.get("http://"+ip + ":5000/tlsa?domain=" + domain,timeout=2)
    json = resp.json()
    publicIP = workerIP(worker)

    if "tlsa" in json:
        tlsa = json['tlsa']
        return "<h1>Domain: " + domain + "</h1><br><p>IP: " + publicIP + "</p><br><p>TLSA: " + tlsa + "</p><br><p>Make sure to add the TLSA record to `_443._tcp." + domain + "` or `*." + domain + "`</p>"
    else:
        return "<h1>Domain: " + domain + "</h1><br><p>IP: " + publicIP + "</p><br><p>TLSA: none</p><br><p>No TLSA record found</p>"

@app.route('/tlsa', methods=['GET'])
def tlsa():
    domain = request.args.get('domain')
    domain = domain.lower()
    if domain == None:
        return jsonify({'error': 'Invalid domain', 'success': 'false'})
    
    # Check if domain exists
    if not site_exists(domain):
        return jsonify({'error': 'Domain does not exist', 'success': 'false'})
    
    # Get worker
    worker = site_worker(domain)
    if worker == None:
        return jsonify({'error': 'Domain does not exist', 'success': 'false'})
    
    # Get worker ip
    ip = workerIP_PRIV(worker)

    # Get TLSA record
    resp=requests.get("http://"+ip + ":5000/tlsa?domain=" + domain,timeout=2)


    return resp.json()


@app.route('/stripe', methods=['POST'])
def stripeapi():
    payload = request.data
    stripe.api_key = os.getenv('STRIPE_SECRET')
    endpoint_secret = os.getenv('STRIPE_ENDPOINT_SECRET')
    sig_header = request.headers.get('Stripe-Signature')
    events = None
    try:
        event = stripe.Webhook.construct_event(
        payload, sig_header, endpoint_secret
        )
    except ValueError as e:
    # Invalid payload
        return jsonify({'success': 'false'})
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'success': 'false'})
    
    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        # Get email
        email = payment_intent['receipt_email']
        # Create licence key
        licence_key = os.urandom(16).hex()
        # Add licence key to file
        key_file = open('/data/licence_key.txt', 'a')
        key_file.write(licence_key + '\n')
        key_file.close()
        # Send email
        host = os.getenv('SMTP_HOST')
        port = os.getenv('SMTP_PORT')
        user = os.getenv('SMTP_USER')
        password = os.getenv('SMTP_PASS')
        from_email = os.getenv('SMTP_FROM')
        if from_email == None:
            from_email = "Hosting <"+user + ">"
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context) as server:
            server.login(user, password)
            message = "From: " + from_email + "\nTo: " + email + \
                "\nSubject: Your Licence key\n\nHello,\n\n"\
                +"This email contains your licence key for your new wordpress site.\n" \
                +"You can redeem this key via the discord bot or at https://hnshosting.au/register\n\n"\
                +"Your licence key is: " + licence_key +"\nThanks,\nHNSHosting"

            server.sendmail(from_email, email, message)

        print('Licence sent via email for stripe payment', flush=True)
    else:
        print('Unhandled event type {}'.format(event.type))
    return jsonify({'success': 'true'})


def get_sites_count():
    # If file doesn't exist, create it
    try:
        sites_file = open('/data/sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('/data/sites.txt', 'w')
        sites_file.close()
        sites_file = open('/data/sites.txt', 'r')
    num=len(sites_file.readlines())
    sites_file.close()
    # Return number of lines in file
    return num

def site_exists(domain):
    # If file doesn't exist, create it
    try:
        sites_file = open('/data/sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('/data/sites.txt', 'w')
        sites_file.close()
        sites_file = open('/data/sites.txt', 'r')

    contains_site = False
    for line in sites_file.readlines():
        if domain == line.split(':')[0]:
            contains_site = True
            break

    sites_file.close()
    return contains_site

def site_worker(domain):
    # If file doesn't exist, create it
    try:
        sites_file = open('/data/sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('/data/sites.txt', 'w')
        sites_file.close()
        sites_file = open('/data/sites.txt', 'r')

    worker = None
    for line in sites_file.readlines():
        if domain == line.split(':')[0]:
            worker = line.split(':')[1].strip('\n')
            break

    sites_file.close()
    return worker

def workerIP_PRIV(worker):
    # If file doesn't exist, create it
    try:
        workers_file = open('/data/workers.txt', 'r')
    except FileNotFoundError:
        workers_file = open('/data/workers.txt', 'w')
        workers_file.close()
        workers_file = open('/data/workers.txt', 'r')

    ip = None
    for line in workers_file.readlines():
        if worker == line.split(':')[0]:
            ip = line.split(':')[1].strip('\n')
            break

    workers_file.close()
    return ip
    
def workerIP(worker):
    # If file doesn't exist, create it
    try:
        workers_file = open('/data/workers.txt', 'r')
    except FileNotFoundError:
        workers_file = open('/data/workers.txt', 'w')
        workers_file.close()
        workers_file = open('/data/workers.txt', 'r')

    ip = None
    for line in workers_file.readlines():
        if worker == line.split(':')[0]:
            ip = line.split(':')[2].strip('\n')
            break

    workers_file.close()
    return ip
        

# Home page
@app.route('/')
def home():
    # Show index template
    # Get site info
    sites = []
    try:
        sites_file = open('/data/sites.txt', 'r')
        sites = sites_file.readlines()
        sites_file.close()
    except FileNotFoundError:
        pass

    
    return render_template('index.html', site_count = str(len(sites)))

# Register page
@app.route('/register', methods=['GET'])
def register():
    buy_licence_link = os.getenv('BUY_LICENCE_LINK')

    # Show register template
    return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="")

@app.route('/register', methods=['POST'])
def register_post():
    buy_licence_link = os.getenv('BUY_LICENCE_LINK')
    if 'licence' not in request.form:
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="No licence key provided")
        
    licence_key = request.form['licence']
    # Check if licence key is valid
    key_file = open('/data/licence_key.txt', 'r')
    valid_key = False
    for line in key_file.readlines():
        if licence_key == line.strip('\n'):
            valid_key = True
            break
    key_file.close()
    if not valid_key:
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="Invalid licence key")
    
    # Get domain
    domain = request.form['domain']
    if domain == None:
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="No domain provided")
    # Check if domain already exists
    if site_exists(domain):
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="Domain already exists")

    # Check if domain contains http:// or https://
    if domain.startswith("http://") or domain.startswith("https://"):
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="Domain should not contain http:// or https://")
    
    # Set domain to lowercase
    domain = domain.lower()

    # Check if worker file exists
    workers = None
    try:
        worker_file = open('/data/workers.txt', 'r')
        workers = worker_file.readlines()
        worker_file.close()
    except FileNotFoundError:
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="No workers available\nPlease contact support")
    
    # Get a worker that has available slots
    worker = None
    for line in workers:
        if not line.__contains__(':'):
            continue
        ip = line.split(':')[1].strip('\n')
        resp=requests.get("http://"+ip + ":5000/status",timeout=2)
        if (resp.status_code == 200):
            if resp.json()['availability'] == True:
                worker = line
                break

    if worker == None:
        return render_template('register.html', buy_licence_link=buy_licence_link, ERROR_MESSAGE="No workers available\nPlease contact support")
    
    # Delete licence key
    key_file = open('/data/licence_key.txt', 'r')
    lines = key_file.readlines()
    key_file.close()
    key_file = open('/data/licence_key.txt', 'w')
    for line in lines:
        if line.strip("\n") != licence_key:
            key_file.write(line)
    key_file.close()
    
    # Add domain to file
    sites_file = open('/data/sites.txt', 'a')
    sites_file.write(domain + ':' + worker.split(':')[0] + '\n')
    sites_file.close()

    # Send worker request
    requests.post("http://"+ worker.split(':')[1].strip('\n') + ":5000/new-site?domain=" + domain)

    return redirect('/success?domain=' + domain + '&status=creating')

@app.route('/success')
def success():
    if 'domain' not in request.args:
        return redirect('/')
    domain = request.args.get('domain')
    domain = domain.lower()
    if not site_exists(domain):
        return render_template('success.html', title="Your site is installing.<br>Please wait...",message="")
    
    if 'status' not in request.args:
        # Get worker
        worker = site_worker(domain)
        if worker == None:
            return render_template('success.html', title="Your site is installing.<br>Please wait...",message="Error: Domain does not exist<br>Please contact support")
        # Get worker ip
        ip = workerIP_PRIV(worker)

        # Get TLSA record
        resp=requests.get("http://"+ip + ":5000/tlsa?domain=" + domain,timeout=2)
        json = resp.json()
        publicIP = workerIP(worker)

        if "tlsa" in json:
            tlsa = json['tlsa']
            return render_template('success.html', title="Your site is ready!",message="Success<br>Domain: " + domain + "<br>IP: " + publicIP + "<br>TLSA: " + tlsa + "<br>Make sure to add the TLSA record to <code>_443._tcp." + domain + "</code> or <code>*." + domain + "</code>")
        else:
            return render_template('success.html', title="Your site is installing.<br>Please wait...",message="Domain: " + domain + "<br>IP: " + publicIP + "<br>TLSA: Pending<br>No TLSA record found")
        
    elif request.args.get('status') == 'creating':
        return render_template('success.html')
    
    
@app.route('/site-count')
def site_count_route():
    return str(get_sites_count())



# Admin page
@app.route('/admin')
def admin():
    # Check if logged in
    login_key = request.cookies.get('login_key')

    if login_key == None:
        return "<h1>Admin</h1><br><form action='/login' method='POST'><input type='password' name='password'><input type='submit' value='Login'></form>"
    if login_key not in logins:
        return "<h1>Admin</h1><br><form action='/login' method='POST'><input type='password' name='password'><input type='submit' value='Login'></form>"
    
    # Show some admin stuff
    licences = []
    try:
        licences_file = open('/data/licence_key.txt', 'r')
        licences = licences_file.readlines()
        licences_file.close()
    except FileNotFoundError:
        pass

    # Create html page
    html = "<h1>Admin</h1><br>"
    html += "<h2>Licences</h2>"
    html += "<p>Number of licences: " + str(len(licences)) + "</p>"
    html += "<p>Licences:</p>"
    html += "<ul>"
    for licence in licences:
        html += "<li>" + licence.strip('\n') + "</li>"
    html += "</ul>"
    html += "<h2>API</h2>"
    html += "<p>API key: " + os.getenv('LICENCE_KEY') + "</p>"
    html += "<p>Worker key: " + os.getenv('WORKER_KEY') + "</p>"
    html += "<h2>Stripe</h2>"
    # Check if stripe is enabled
    if os.getenv('STRIPE_SECRET') == None:
        html += "<p>Stripe is not enabled</p>"
    else:
        html += "<p>Stripe is enabled</p>"
    
    html += "<br><br><h2>Workers</h2>"
    workers = []
    try:
        workers_file = open('/data/workers.txt', 'r')
        workers = workers_file.readlines()
        workers_file.close()
    except FileNotFoundError:
        pass

    for worker in workers:
        if not worker.__contains__(':'):
            continue

        html += "<p>Name: " + worker.split(':')[0] + " | Public IP " + worker.split(':')[2].strip('\n') + " | Private IP " + worker.split(':')[1]
        # Check worker status
        online=True
        try:
            resp=requests.get("http://"+worker.split(':')[1].strip('\n') + ":5000/status",timeout=2)
            if (resp.status_code != 200):
                html += " | Status: Offline"
            else:
                html += " | Status: Online | Sites: " + str(resp.json()['num_sites']) + " | Availability: " + str(resp.json()['availability'])
        except:
            html += " | Status: Offline"
            
        html += "</p>"
        

    html += "<h2>Sites</h2>"
    sites = []
    try:
        sites_file = open('/data/sites.txt', 'r')
        sites = sites_file.readlines()
        sites_file.close()
    except FileNotFoundError:
        pass

    for site in sites:
        if not site.__contains__(':'):
            continue
        domain = site.split(':')[0]
        html += "<p>Domain: <a href='https://"+ domain + "'>" + domain + "</a> | Worker: " + site.split(':')[1].strip('\n') + " | <a href='/info?domain=" + domain + "'>Info</a></p>"

    html += "<br><br>"
    # Form to add worker
    html += "<h2>Add worker</h2>"
    html += "<form action='/new-worker' method='POST'>"
    html += "<p>Name: <input type='text' name='name'></p>"
    html += "<p>Public IP: <input type='text' name='ip'></p>"
    html += "<p>Private IP: <input type='text' name='priv'></p>"
    html += "<input type='submit' value='Add worker'>"
    html += "</form>"
    
    html += "<br><h2><a href='/licence'>Add Licence</a></h2><br>"
    # Form to add site
    html += "<h2>Add site</h2>"
    html += "<form action='/add-site' method='POST'>"
    html += "<p>Domain: <input type='text' name='domain'></p>"
    html += "<input type='submit' value='Add site'>"
    html += "</form>"
    

    html += "<br><a href='/logout'>Logout</a></h2>"


    return html
    

@app.route('/add-site', methods=['POST'])
def addsite():
    # Check for licence key
    if 'licence' not in request.form:
        # Check cookie
        login_key = request.cookies.get('login_key')
        if login_key == None:
            return redirect('/admin')
        if login_key not in logins:
            return redirect('/admin')    
    else:
        # Use licence key
        licence_key = request.form['licence']
        # Check if licence key is valid
        key_file = open('/data/licence_key.txt', 'r')
        valid_key = False
        for line in key_file.readlines():
            if licence_key == line.strip('\n'):
                valid_key = True
                break
        key_file.close()
        if not valid_key:
            return jsonify({'error': 'Invalid licence', 'success': 'false'})
        
        # Delete licence key
        key_file = open('/data/licence_key.txt', 'r')
        lines = key_file.readlines()
        key_file.close()
        key_file = open('/data/licence_key.txt', 'w')
        for line in lines:
            if line.strip("\n") != licence_key:
                key_file.write(line)
        key_file.close()

    # Get domain
    domain = request.form['domain']
    if domain == None:
        return jsonify({'error': 'No domain sent', 'success': 'false'})
    # Check if domain already exists
    if site_exists(domain):
        return jsonify({'error': 'Domain already exists', 'success': 'false'})
    
    # Check if domain contains http:// or https://
    if domain.startswith("http://") or domain.startswith("https://"):
        return jsonify({'error': 'Domain should not contain http:// or https://', 'success': 'false'})
    
    domain = domain.lower()
    # Check if worker file exists
    workers = None
    try:
        worker_file = open('/data/workers.txt', 'r')
        workers = worker_file.readlines()
        worker_file.close()
    except FileNotFoundError:
        return jsonify({'error': 'No workers available', 'success': 'false'})
    
    # Get a worker that has available slots
    worker = None
    for line in workers:
        if not line.__contains__(':'):
            continue

        ip = line.split(':')[1].strip('\n')
        resp=requests.get("http://"+ip + ":5000/status",timeout=2)
        if (resp.status_code == 200):
            if resp.json()['availability'] == True:
                worker = line
                break
    
    if worker == None:
        return jsonify({'error': 'No workers available', 'success': 'false'})


    # Add domain to file
    sites_file = open('/data/sites.txt', 'a')
    sites_file.write(domain + ':' + worker.split(':')[0] + '\n')
    sites_file.close()

    # Send worker request
    requests.post("http://"+ worker.split(':')[1].strip('\n') + ":5000/new-site?domain=" + domain)

    html = "<h1>Site creating...</h1><br>"
    html += "<p>Domain: " + domain + "</p>"
    html += "<p>Worker: " + worker.split(':')[0] + "</p>"
    html += "<p>Worker IP: " + worker.split(':')[1].strip('\n') + "</p>"
    html += "<p><a href='/info?domain=" + domain + "'>Check status</a></p>"

    return html
    

@app.route('/licence')
def licence():
    # Check cookie
    login_key = request.cookies.get('login_key')
    if login_key == None:
        return redirect('/admin')
    if login_key not in logins:
        return redirect('/admin')
    
    licence_key = os.urandom(16).hex()

    # Add license key to file
    key_file = open('/data/licence_key.txt', 'a')
    key_file.write(licence_key + '\n')
    key_file.close()

    return "<h1>Licence key</h1><br><p>" + licence_key + "</p><br><a href='/admin'>Back</a>"
    


@app.route('/new-worker', methods=['POST'])
def new_worker():
    # Check cookie
    login_key = request.cookies.get('login_key')

    if login_key == None:
        return redirect('/admin')
    if login_key not in logins:
        return redirect('/admin')
    
    worker = request.form['name']
    worker_IP = request.form['ip']
    worker_PRIV = request.form['priv']


    # Check worker file
    try:
        workers_file = open('/data/workers.txt', 'r')
    except FileNotFoundError:
        workers_file = open('/data/workers.txt', 'w')
        workers_file.close()
        workers_file = open('/data/workers.txt', 'r')
    
    # Check if worker already exists
    if worker in workers_file.read():
        return jsonify({'error': 'Worker already exists', 'success': 'false'})
    
    workers_file.close()

    # Add worker to file
    workers_file = open('/data/workers.txt', 'a')
    workers_file.write(worker + ":" + worker_PRIV + ":"+ worker_IP + '\n')
    workers_file.close()

    return redirect('/admin')    


@app.route('/logout')
def logout():
    login_key = request.cookies.get('login_key')
    if login_key == None:
        return redirect('/admin')
    if login_key not in logins:
        return redirect('/admin')
    
    logins.remove(login_key)
    return redirect('/admin')


@app.route('/login', methods=['POST'])
def login():
    # Handle login
    print('Login attempt', flush=True)
    # Check if form contains password
    if 'password' not in request.form:
        print('Login failed', flush=True)
        return redirect('/failed-login')

    password = request.form['password']
    if os.getenv('ADMIN_KEY') == password:
        print('Login success', flush=True)
        # Generate login key
        login_key = os.urandom(32).hex()
        logins.append(login_key)
        # Set cookie
        resp = make_response(redirect('/admin'))
        resp.set_cookie('login_key', login_key)
        return resp
    print('Login failed', flush=True)
    return redirect('/failed-login')

@app.route('/failed-login')
def failed_login():
    return "<h1>Failed login</h1><br><form action='/login' method='POST'><input type='password' name='password'><input type='submit' value='Login'></form>"

# Assets
@app.route('/assets/<path:path>')
def send_report(path):
    return send_from_directory('templates/assets', path)
    



# Start the server
if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')