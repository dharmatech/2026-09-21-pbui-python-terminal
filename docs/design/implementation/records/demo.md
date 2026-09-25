# Try JSON records and DataFrames

This tour turns Treasury's current debt records into a frame, then turns the
frame back into JSON records. The listener keeps each source in its history.

## Start

From the project root, launch the full-screen listener:

```console
uv run pbui
```

Type commands in the input row at the bottom of the screen. Use the right
mouse button on a retained Value to open its action menu; use the left button
to inspect it. Press `Ctrl-C` to stop the listener. This tour only reads the
public endpoint and does not change files or processes. The debt figures and
the number of returned records change over time.

## Steps

1. Enter this as one line in the input row:

   ```text
   :get https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=10&fields=record_date,tot_pub_debt_out_amt
   ```

   The listener adds a GET request to history. Open its menu and choose
   `perform`. The response appears below it.

2. Open the response's menu and choose `json`. Left-click the resulting JSON
   object to list its members. Left-click `data` to retain the array of debt
   records. The array's documentation says `Left: list members • Right: menu`.

3. Open the array's menu and choose `To DataFrame`. A new frame Value appears;
   the original array stays in history. The frame has one row per returned
   record, with columns including `record_date` and `tot_pub_debt_out_amt`.
   Left-click the frame to see its bounded preview and read those columns.
   Debt amounts remain text when the API supplied JSON strings.

4. Open that frame's menu and choose `To JSON records`. A new JSON array
   appears below the saved action. Left-click it to list its immediate record
   objects. The frame and the first array remain available in history until
   normal history eviction removes old rows.

If the endpoint is unavailable, the listener displays an Error for the
request. The conversion actions can still be tried on locally retained JSON
Values and frames.
