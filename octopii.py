"""
MIT License

Copyright (c) Research @ RedHunt Labs Pvt Ltd
Written by Owais Shaikh
Email: owais.shaikh@redhuntlabs.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

output_file = "output.json"

import os, sys, json, shutil
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import cv2
import file_utils
import urllib
from pdf2image import convert_from_path
import json, textract, sys
import image_utils, file_utils, text_utils

model_file_name = 'models/other_pii_model.h5'
labels_file_name = 'models/other_pii_model.txt'
temp_dir = "OCTOPII_TEMP/"

def print_logo():
    logo = '''⠀⠀⠀ ⠀⡀⠀⠀⠀⢀⢀⠀⠀⠀⢀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠈⠋⠓⡅⢸⣝⢷⡅⢰⠙⠙⠁⠀⠀⠀⠀
⠀⢠⣢⣠⡠⣄⠀⡇⢸⢮⡳⡇⢸⠀⡠⡤⡤⡴⡄⠀   O C T O P I I 
⠀⠀⠀⠀⠀⡳⠀⠧⣤⡳⣝⢤⠼⠀⡯⠀⠀⠈⠀⠀   A PII scanner  
⠀⠀⠀⠀⢀⣈⣋⣋⠮⡻⡪⢯⣋⢓⣉⡀⠀⠀⠀⠀(c) 2023 RedHunt Labs Pvt Ltd        
⠀⠀⠀⢀⣳⡁⡡⣅⠀⡗⣝⠀⡨⣅⢁⣗⠀⠀⠀⠀
⠀⠀⠀⠀⠈⠀⠸⣊⣀⡝⢸⣀⣸⠊⠀⠉⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠈⠈⠀⠀⠈⠈'''
    print (logo)

def help_screen():
    help = '''Usage: python octopii.py <file, local path or URL>
Note: Only Unix-like filesystems, S3 and open directory URLs are supported.

Reach out to owais.shaikh@redhuntlabs.com for queries'''
    print(help)

def search_pii(file_path):
    if (file_utils.is_image(file_path)):
        image = cv2.imread(file_path)
        contains_faces = image_utils.scan_image_for_people(image)

        original, intelligible = image_utils.scan_image_for_text(image)
        text = original

    elif (file_utils.is_pdf(file_path)):
        pdf_pages = convert_from_path(file_path, 400) # Higher DPI reads small text better
        for page in pdf_pages:
            contains_faces = image_utils.scan_image_for_people(page)

            original, intelligible = image_utils.scan_image_for_text(page)
            text = original

    else:
        try:
            text = textract.process(file_path).decode()
            intelligible = text_utils.string_tokenizer(text)
        except textract.exceptions.MissingFileError:
            print ("Couldn't find file '" + file_path + "'")
            exit(-1)

    addresses = text_utils.regional_pii(text)
    emails = text_utils.email_pii(text, rules)
    phone_numbers = text_utils.phone_pii(text, rules)

    keywords_scores = text_utils.keywords_classify_pii(rules, intelligible)
    score = max(keywords_scores.values())
    pii_class = list(keywords_scores.keys())[list(keywords_scores.values()).index(score)]

    country_of_origin = rules[pii_class]["region"]

    identifiers = text_utils.id_card_numbers_pii(text, rules)

    if score < 5:
        pii_class = None

    if len(identifiers) != 0:
        identifiers = identifiers[0]["result"]

    if temp_dir in file_path:
        file_path = file_path.replace(temp_dir, "")
        file_path = urllib.parse.unquote(file_path)

    result = {
        "file_path" : file_path,
        "pii_class" : pii_class,
        "score" : score,
        "country_of_origin": country_of_origin,
        "faces" : contains_faces,
        "identifiers" : identifiers,
        "emails" : emails,
        "phone_numbers" : phone_numbers,
        "addresses" : addresses
    }

    return result
    

if __name__ in '__main__':

    if len(sys.argv) > 1:
        location = sys.argv[1] 
    else: 
        print_logo()
        help_screen()
        exit(-1)

    rules=text_utils.get_regexes()

    files = []
    items = []

    temp_exists = False

    print("Scanning '" + location + "'")

    if "http" in location:
        try:
            file_urls = []
            _, extension = os.path.splitext(location)
            if extension != "":
                file_urls.append(location)
            else:
                files = file_utils.list_local_files(location)

            file_urls = file_utils.list_s3_files(location)
            if len(file_urls) != 0:
                try:
                    shutil.rmtree(temp_dir)
                except: pass
                temp_exists = True
                os.makedirs(os.path.dirname(temp_dir))
                for url in file_urls:
                    file_name = urllib.parse.quote(url, "UTF-8")
                    urllib.request.urlretrieve(url, temp_dir+file_name)

        except:
            try:
                files = file_utils.list_directory_files(location)
                if len(file_urls) != 0:
                    try:
                        shutil.rmtree(temp_dir)
                    except: pass
                    temp_exists = True
                    os.makedirs(os.path.dirname(temp_dir))
                    for url in file_urls:
                        encoded_url = urllib.parse.quote(url, "UTF-8")
                        urllib.request.urlretrieve(url, temp_dir + encoded_url)
            except:
                print ("This URL is not a valid S3 or has no directory listing enabled. Try running Octopii on these files locally.")
                sys.exit(-1)

        files = file_utils.list_local_files(temp_dir)

    else:
        _, extension = os.path.splitext(location)
        if extension != "":
            files.append(location)
        else:
            files = file_utils.list_local_files(location)

    if len(files) == 0:
        print ("Invalid path provided. Please provide a non-empty directory or a file as an argument.")
        sys.exit(0)

    for file_path in files:
        results = search_pii (file_path)
        print(json.dumps(results, indent=4))
        file_utils.append_to_output_file(results, output_file)

    print ("Output saved in " + output_file)

    if temp_exists: shutil.rmtree(temp_dir)

    sys.exit(0)
            