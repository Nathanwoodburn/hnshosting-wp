from flask import Flask, request, jsonify
import dotenv
import os
import requests

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
    key_file = open('licence_key.txt', 'a')
    key_file.write(licence_key + '\n')
    key_file.close()

    return jsonify({'success': "true", 'licence_key': licence_key})


@app.route('/new-site', methods=['POST'])
def new_site():
    domain=request.args.get('domain')
    # Get API header
    api_key = request.headers.get('key')
    
    # Verify both API key and domain exist
    if api_key == None or domain == None:
        return jsonify({'error': 'Invalid API key or domain', 'success': 'false'})

    # Check if API key is a valid site key
    if api_key not in open('licence_key.txt', 'r').read():
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
        worker_file = open('workers.txt', 'r')
        workers = worker_file.readlines()
        worker_file.close()
    except FileNotFoundError:
        return jsonify({'error': 'No workers available', 'success': 'false'})
    
    # Get a worker that has available slots
    worker = None
    for line in workers:
        ip = line.split(':')[1].strip('\n')
        resp=requests.get("http://"+ip + ":5000/status",timeout=2)
        if (resp.status_code == 200):
            if resp.json()['availability'] == True:
                worker = line
                break
    
    if worker == None:
        return jsonify({'error': 'No workers available', 'success': 'false'})


    # Add domain to file
    sites_file = open('sites.txt', 'a')
    sites_file.write(domain + ':' + worker.split(':')[0] + '\n')
    sites_file.close()

    # Use key
    key_file = open('licence_key.txt', 'r')
    lines = key_file.readlines()
    key_file.close()
    key_file = open('licence_key.txt', 'w')
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
        workers_file = open('workers.txt', 'r')
    except FileNotFoundError:
        workers_file = open('workers.txt', 'w')
        workers_file.close()
        workers_file = open('workers.txt', 'r')
    
    # Check if worker already exists
    if worker in workers_file.read():
        return jsonify({'error': 'Worker already exists', 'success': 'false'})
    
    workers_file.close()

    # Add worker to file
    workers_file = open('workers.txt', 'a')
    workers_file.write(worker + ":" + worker_IP + '\n')
    workers_file.close()

    online=True
    resp=requests.get("http://"+worker_IP + ":5000/ping",timeout=2)
    if (resp.status_code != 200):
        online=False

    return jsonify({'success': 'true', 'worker': worker, 'online': online})


def get_sites_count():
    # If file doesn't exist, create it
    try:
        sites_file = open('sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('sites.txt', 'w')
        sites_file.close()
        sites_file = open('sites.txt', 'r')
    num=len(sites_file.readlines())
    sites_file.close()
    # Return number of lines in file
    return num

def site_exists(domain):
    # If file doesn't exist, create it
    try:
        sites_file = open('sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('sites.txt', 'w')
        sites_file.close()
        sites_file = open('sites.txt', 'r')

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
        sites_file = open('sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('sites.txt', 'w')
        sites_file.close()
        sites_file = open('sites.txt', 'r')

    worker = None
    for line in sites_file.readlines():
        if domain == line.split(':')[0]:
            worker = line.split(':')[1].strip('\n')
            break

    sites_file.close()
    return worker
        

# Start the server
if __name__ == '__main__':
    app.run(debug=False, port=4000)