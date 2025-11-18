# Updating Doctor Statuses and Admin Filters

Follow the steps below to ensure your workspace matches the latest fixes:

1. **Sync the latest code**
   1. `git fetch origin`
   2. `git checkout work`
   3. `git pull`

2. **Update `DoctorProfile.STATUS_CHOICES`**
   1. Open `mysite/booking/models.py`.
   2. Replace the old `STATUS_CHOICES` tuple with the expanded list that includes `Pending`, `Approved`, `Rejected`, `Active`, and `Inactive`.
   3. Ensure the `status` field still defaults to `"Pending"` and uses `max_length=10`.

3. **Add the Appointment `datetime` property**
   1. Locate the `Appointment` model inside `mysite/booking/models.py`.
   2. Remove the custom `__init__` override if it exists.
   3. Add the `datetime` property exactly as shown in the final file section below so downstream code can safely combine the stored `date` and `time` values.

4. **Create migration 0007**
   1. Run `python manage.py makemigrations booking`.
   2. Confirm Django generates `mysite/booking/migrations/0007_alter_doctorprofile_status.py` that expands the status choices to match the model.
   3. Verify the file contents match the version shown below.

5. **Update the admin doctor list view**
   1. Edit `mysite/booking/views.py`.
   2. In `admin_doctors`, ensure you:
      - Read `search` and `status` query parameters.
      - Apply `Q` filters based on the search string across first name, last name, specialization, hospital, and city.
      - Filter by status when the value is set to something other than `"all"`.
      - Order the queryset by the doctor’s first name.
      - Pass the selected filter values back in the template context (keys: `search_query` and `status_filter`).
      - Keep the activate/deactivate POST handling logic unchanged.

6. **Run migrations and tests**
   1. `python manage.py migrate`
   2. `python manage.py test`

7. **Review and commit**
   1. `git status`
   2. `git add mysite/booking/models.py mysite/booking/views.py mysite/booking/migrations/0007_alter_doctorprofile_status.py`
   3. `git commit -m "Fix doctor statuses and admin filters"`

8. **Create the PR**
   1. Push your branch.
   2. Open a pull request summarizing the changes.

Refer to the sections below for the exact contents of the updated files.
