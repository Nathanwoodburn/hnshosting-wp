from flask import Flask, request, jsonify
import dotenv
import os
import requests
import stripe # For stripe payments
import smtplib, ssl # For sending emails

dotenv.load_dotenv()


app = Flask(__name__)

# API add license key (requires API key in header)
@app.route('/add-licence', methods=['POST'])
def add_license():
    # Get API header
    api_key = request.headers.get('key')
    if api_key != os.getenv('LICENCE-API'):
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
        return jsonify({'error': 'Missing API key', 'success': 'false'})
    
    if domain == None:
        return jsonify({'error': 'Missing domain', 'success': 'false'})

    # Check if API key is a valid site key
    if api_key not in open('/data/licence_key.txt', 'r').read():
        return jsonify({'error': 'Invalid API key', 'success': 'false'})
    
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
    # Get API header
    api_key = request.headers.get('key')
    if api_key == None or worker == None or worker_IP == None:
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
    workers_file.write(worker + ":" + worker_IP + '\n')
    workers_file.close()

    online=True
    resp=requests.get("http://"+worker_IP + ":5000/ping",timeout=2)
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
        resp=requests.get("http://"+worker.split(':')[1].strip('\n') + ":5000/status",timeout=2)
        if (resp.status_code != 200):
            online=False
            worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[1].strip('\n'), 'online': online, 'sites': 0, 'status': 'offline'})
            continue
        sites = resp.json()['num_sites']
        availability = resp.json()['availability']
        if availability == True:
            worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[1].strip('\n'), 'online': online, 'sites': sites, 'status': 'ready'})
        else:
            worker_list.append({'worker': worker.split(':')[0],'ip': worker.split(':')[1].strip('\n'), 'online': online, 'sites': sites, 'status': 'full'})
    
    if len(worker_list) == 0:
        return jsonify({'error': 'No workers available', 'success': 'false'})
    return jsonify({'success': 'true', 'workers': worker_list})

@app.route('/site-info', methods=['GET'])
def site_status():
    domain = request.args.get('domain')
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
    ip = workerIP(worker)

    # Get TLSA record
    resp=requests.get("http://"+ip + ":5000/tlsa?domain=" + domain,timeout=2)
    json = resp.json()

    if "tlsa" in json:
        tlsa = json['tlsa']
        return jsonify({'success': 'true', 'domain': domain, 'ip': ip, 'tlsa': tlsa})
    else:
        return jsonify({'success': 'false', 'domain': domain, 'ip': ip, 'tlsa': 'none','error': 'No TLSA record found'})


@app.route('/tlsa', methods=['GET'])
def tlsa():
    domain = request.args.get('domain')
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
    ip = workerIP(worker)

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
                +"You can redeem this key via the discord bot or api.\n\n"\
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
            ip = line.split(':')[1].strip('\n')
            break

    workers_file.close()
    return ip
    
        

# Start the server
if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')