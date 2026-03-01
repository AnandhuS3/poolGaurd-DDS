# Phone Number Migration Guide

## Overview
The system has been updated to support international phone numbers using the E.164 standard format.

## E.164 Format
The E.164 format is the international standard for phone numbers:
```
+[country code][subscriber number]
```

### Examples:
- **India:** `+91 9876543210`
- **USA:** `+1 5551234567`
- **UK:** `+44 7911123456`
- **Australia:** `+61 412345678`

## For Users

### Registration
1. Select your country from the dropdown (defaults to India 🇮🇳 +91)
2. Enter your phone number **without** the country code
3. The system automatically combines them in E.164 format

### Supported Countries (Default)
- 🇮🇳 India (+91)
- 🇺🇸 USA/Canada (+1)
- 🇬🇧 United Kingdom (+44)
- 🇦🇺 Australia (+61)
- 🇯🇵 Japan (+81)
- 🇨🇳 China (+86)
- 🇫🇷 France (+33)
- 🇩🇪 Germany (+49)
- 🇦🇪 UAE (+971)
- 🇸🇬 Singapore (+65)

## For Developers

### Adding New Countries
Edit `core/region_utils.py` and add to `COUNTRY_CODES` list:

```python
COUNTRY_CODES = [
    # ... existing codes ...
    {'code': '+XX', 'name': 'Country Name', 'flag': '🏴', 'pattern': r'^\d{X}$'},
]
```

Then update `frontend/register.html` dropdown:

```html
<option value="+XX">🏴 +XX</option>
```

### Validation
Phone numbers are validated using the `validate_phone_number()` function from `region_utils`:

```python
from core.region_utils import validate_phone_number

# Returns True/False
is_valid = validate_phone_number("+91 9876543210")
```

### Formatting
Use `format_phone_number()` to ensure E.164 compliance:

```python
from core.region_utils import format_phone_number

# With country code
formatted = format_phone_number("9876543210", "+91")
# Returns: "+919876543210"

# Already formatted
formatted = format_phone_number("+91 9876543210")
# Returns: "+919876543210"
```

## Database Considerations

### Storage
- Phone numbers are stored in E.164 format: `+[country][number]`
- VARCHAR(20) is sufficient for most international numbers
- Always store with the `+` prefix

### Migration
If you have existing data with India-only format:

```sql
-- Example migration (adjust as needed)
UPDATE users 
SET phone_number = CONCAT('+91', phone_number) 
WHERE phone_number NOT LIKE '+%' 
  AND LENGTH(phone_number) = 10;
```

## API Integration

### SMS/WhatsApp Services
Most services (Twilio, MSG91, etc.) accept E.164 format natively:

```python
# Twilio example
client.messages.create(
    to="+919876543210",  # E.164 format
    from_="+1234567890",
    body="Alert message"
)
```

### Email Notifications
Phone numbers are displayed in formatted E.164 in emails for clarity.

## Timezone Configuration

### Environment Variable
Set the system timezone via environment variable:

```bash
export SYSTEM_TIMEZONE="America/New_York"
```

Default: `Asia/Kolkata` (IST)

### Supported Timezones
Any valid pytz timezone string:
- `America/New_York` (EST/EDT)
- `Europe/London` (GMT/BST)
- `Asia/Tokyo` (JST)
- `Australia/Sydney` (AEST/AEDT)
- etc.

## Troubleshooting

### "Phone number must include country code"
**Solution:** Ensure the phone number starts with `+` and includes the country code.

### "Invalid phone number format"
**Solution:** Check that:
1. Number starts with `+`
2. Country code is 1-3 digits
3. Total length is 8-15 digits (including country code)

### Registration fails with phone validation error
**Solution:** 
1. Select the correct country from dropdown
2. Enter only the subscriber number (without country code)
3. System will combine them automatically

## Best Practices

1. **Always validate** phone numbers before storing
2. **Store in E.164** format in database
3. **Display formatted** for user readability (e.g., "+91 98765 43210")
4. **Use region_utils** functions for consistency
5. **Test with multiple** countries during development

---

For questions or issues, refer to:
- `core/region_utils.py` - Phone utilities
- `core/auth.py` - Validation logic
- `frontend/register.html` - UI implementation
