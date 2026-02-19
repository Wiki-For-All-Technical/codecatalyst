G2COMMONS

A Web application that uploads photos on Wikki Commons
________________________________________
Description :

G2COMMONS is a lightweight, user-friendly Python Flask web application that allows users to upload photos directly to Wikimedia Commons through a web interface.
The goal of this project is to simplify the process of contributing media to Wikimedia projects by providing an easy-to-use upload workflow.
The app handles:
•	Image selection & upload
•	User input for image details (title, description)
•	Integration with Wikimedia Commons API
•	Validation for supported file types
________________________________________
Installation :

1. Clone the repository
git clone https://github.com/Wiki-For-All-Technical/codecatalyst.git
cd codecatalyst
2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows
3. Install dependencies
pip install -r requirements.txt
4. Create the database
CREATE DATABASE codecatalyst;
5. Run the application
python app.py
Access the application at:
http://127.0.0.1:5000/
________________________________________
Usage :

1.	Open the web app in your browser.
2.	Click Upload Photo.
3.	Choose an image file (JPG, PNG, etc.).
4.	Enter the required details:
o	Title
o	Description
5.	Submit the form to upload the image to Wikimedia Commons.
6.	The system will confirm the upload and display the file link.
