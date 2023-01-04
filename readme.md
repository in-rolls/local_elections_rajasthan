## State Election Commission, Rajasthan

Scrape: https://sec.rajasthan.gov.in/grampanchayatdetails.aspx
Iterate over all the dropdowns. We also want data from all the red tabs —-there are 4 of them (Contesting sarpanch, statistics for nomination, Winner Sarpanch (which includes a link to the pdf that we want to save with id = id of the candidate), Ward winning panch)

Final data: (one big CSV or CSVs with clear primary keys)

From the main page: 
Election Type, Election Duration, District, Panchayat Samiti, Gram Panchayat, 

From the contesting sarpanch tab: 

Sr. No., Name of Gram Panchayat, Category of Gram Panchayat, Contesting Candidate Serial No., Name of Contesting Candidate, Father/Husband of Contesting Candidate, Gender, Marital Status, Category of Candidate, Education Status, Contesting Candidate Occupation, Age, Total Value of Capital Assets (Land-Building-Jewelry), Children Before 27 11 1995, Children on or after 28 11 1995, mobile no., email address

From the winner sarpanch: 

Elected unopposed, total electorate votes, total polled votes, rejected votes, total valid votes, poll %, winner candidate name, pledge (pdf_file_name), vote secure by winner, runnerup candidate name, vote secure by runnerup, total number of nota count, tendered votes

Ward winning panch

All the columns and rows 

Statistics for nomination
