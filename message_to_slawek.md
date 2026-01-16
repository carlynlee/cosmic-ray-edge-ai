Subject: Issue with credo-data-exporter.py - Export files never become available

Hi Slawek,

I've been using the `credo-data-exporter.py` script from https://github.com/credo-science/credo-api-tools and encountered an issue where the script hangs indefinitely waiting for export files that never become available.

**Problem Summary:**
The script successfully requests exports from the API and receives export URLs, but when polling the S3 URLs, the files never appear (returning 404 or 403 with "NoSuchKey" errors). The script can hang for extended periods waiting for exports that never complete.

**Technical Details:**

1. **Status Code Handling Issue:**
   - The script only checks for `r.status_code == 404` (line 195 in `update_data()`)
   - However, S3 sometimes returns `403 Forbidden` with an XML error body containing `<Code>NoSuchKey</Code>`
   - When a 403 is returned, the script falls through to the `else` block and tries to process it as a successful response, which fails

2. **Export Availability:**
   - API requests succeed and return export URLs immediately
   - Testing shows exports remain unavailable (404/403) even after waiting 2+ minutes
   - This suggests either:
     - The export generation service is not creating files
     - There's no data to export for the requested time range
     - Exports take longer than the script's retry timeout

3. **Minor Bug:**
   - Line 196 has incorrect print message: "Waiting for mapping export to finish" (should say "data export")

**Testing Performed:**
- Network connectivity confirmed working
- API authentication successful
- Export requests return valid URLs
- S3 endpoint accessible
- Export files consistently return 404/403 even after extended waits

**Suggested Fixes:**

1. Handle both 404 and 403 status codes when checking if export is ready:
   ```python
   if r.status_code in [404, 403]:
       # Check if 403 is actually a NoSuchKey error
       if r.status_code == 403:
           try:
               import xml.etree.ElementTree as ET
               root = ET.fromstring(r.text)
               if root.find('.//Code').text != 'NoSuchKey':
                   r.raise_for_status()
           except:
               r.raise_for_status()
   ```

2. Add better error messages to distinguish between "export not ready" vs "no data available"

3. Consider adding a timeout or max retry limit that's more reasonable

Would you like me to create a pull request with these fixes, or is there additional context about how the export service works that I should be aware of?

Thanks for maintaining this tool!

Best regards,
[Your Name]



