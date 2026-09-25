## Day 2 Data Quality Notes

- The downloaded Maharashtra Company Master Data file contains 755,653 company records across multiple ROC codes.
- ROC Pune contains 188,042 records and is the selected jurisdiction for this project; the remaining ROC records are retained in the original raw dataset but are outside the primary analysis scope.
- The dataset contains 16 columns. CompanyName, CompanyROCcode, CompanyRegistrationdate_date, and CompanyStatus have no missing values in the inspected dataset; Registered_Office_Address has 34 missing values.
- CompanyRegistrationdate_date is stored as text in DD-MM-YYYY format. The dataset also contains mixed company statuses, including Active and Strike Off, which will be retained during ingestion and handled during later cleaning/scoring stages.

## Day 3 Cleaning Results

The sampled registered addresses showed inconsistent formatting, including abbreviations such as `Rd`, `Nr`, `Opp`, `MIDC`, `Fl`, `Gat No`, `S No`, and `Plot No`. Company names commonly contained legal suffixes such as `Private Limited` and `Pvt Ltd`.

In the initial sample of 30 addresses, there were no null or blank registered addresses.

After applying the normalization pipeline:

- Addresses normalized successfully: 188,042
- Addresses failed/empty: 0
- Pincodes extracted: 188,011
- Pincodes missing: 31
- Registration dates parsed successfully: 187,985
- Authorized capital values parsed successfully: 142,762

The normalization process converts company names to lowercase, removes legal suffixes and punctuation, normalizes address formatting and abbreviations, extracts six-digit Indian pincodes, and converts capital values into numeric form.