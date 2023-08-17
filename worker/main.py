# API server

from flask import Flask, request, jsonify
import dotenv
import os
import threading

dotenv.load_dotenv()


app = Flask(__name__)

# API route for POST requests for new-site (takes variable 'domain')
@app.route('/new-site', methods=['POST'])
def new_site():
    # Get the URL from the request
    domain = request.args.get('domain')
    count = get_sites_count()

    if site_exists(domain):
        return jsonify({'error': 'Site already exists', 'success': 'false'})

    # Add site to file
    sites_file = open('sites.txt', 'a')
    sites_file.write(domain + '\n')
    sites_file.close()

    # New site in background
    thread = threading.Thread(target=new_site, args=(domain, 5000 + count))
    thread.start()


    # Return the domain and the number of sites
    return jsonify({'domain': domain, 'count': count})

@app.route('/tlsa', methods=['GET'])
def tlsa():
    domain = request.args.get('domain')
    if domain == None:
        return jsonify({'error': 'Invalid domain', 'success': 'false'})
    script = 'bash tlsa.sh ' + domain
    # Get output from script
    tlsa = os.popen(script).read()

    return jsonify({'domain': domain, 'tlsa': tlsa})


# Return status
@app.route('/status', methods=['GET'])
def status():
    num_Sites = get_sites_count()

    availability=(num_Sites < int(os.getenv('MAX_SITES')))
    return jsonify({'availability': availability, 'num_sites': num_Sites})


# Ping status
@app.route('/ping')
def ping():
    return 'pong'

def get_sites_count():
    # If file doesn't exist, create it
    try:
        sites_file = open('sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('sites.txt', 'w')
        sites_file.close()
        sites_file = open('sites.txt', 'r')
    print(sites_file.readlines())
    # Return number of lines in file
    return len(sites_file.readlines())

def site_exists(domain):
    # If file doesn't exist, create it
    try:
        sites_file = open('sites.txt', 'r')
    except FileNotFoundError:
        sites_file = open('sites.txt', 'w')
        sites_file.close()
        sites_file = open('sites.txt', 'r')

    # Check if domain is in file
    if domain in sites_file.read():
        return True
    else:
        return False
    
async def new_site(domain,port):
    script = 'bash wp.sh ' + domain + ' '+ str(port)
    os.system(script)

# Start the server
if __name__ == '__main__':
    app.run(debug=False, port=5000,host='0.0.0.0')