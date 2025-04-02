import gspread
import logging

logger = logging.getLogger(__name__)


def get_sheet_data(credentials, sheet_id, worksheet_name="Sheet1"):
    try:
        client = gspread.authorize(credentials)

        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)

        data = worksheet.get_all_records()
        logger.info(f"Retrieved {len(data)} records from Google Sheets")
        return data

    except Exception as e:
        logger.info(f"Error during daily update: {str(e)}")
        raise
