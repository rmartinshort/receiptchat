# receiptchat
Use generative AI to extract information from receipts

## Try it out

- Make sure tesseract is installed (on mac, can be installed using homebrew or macports)    
- Clone this repo, make a python 3.9+ environment and install the requirements     
- Set up your Google Drive credentials and put them on a file called "gdrive_credentials.json". Store that in the top level directory    
- Set up an OpenAI API key and store it in a .env file in the top level directory   
- Put some receipts in your connected Google Drive folder  
- To run vision extraction (generate the examples), run `driver.main_generate_examples()`. By default only 10 files will be parsed   
- To run text extraction (i.e. with gpt-3.5-turbo learning from examples), run `driver.main()`  

Be aware of your API costs!