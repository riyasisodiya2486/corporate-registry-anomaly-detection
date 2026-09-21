# Data Quality Notes

- The downloaded Maharashtra Company Master Data file contains 755,653 company records across multiple ROC codes.
- ROC Pune contains 188,042 records and is the selected jurisdiction for this project; the remaining ROC records are retained in the original raw dataset but are outside the primary analysis scope.
- The dataset contains 16 columns. CompanyName, CompanyROCcode, CompanyRegistrationdate_date, and CompanyStatus have no missing values in the inspected dataset; Registered_Office_Address has 34 missing values.
- CompanyRegistrationdate_date is stored as text in DD-MM-YYYY format. The dataset also contains mixed company statuses, including Active and Strike Off, which will be retained during ingestion and handled during later cleaning/scoring stages.