# Step-by-step: Updating Doctor Statuses, Appointments, and Admin Filters

This checklist assumes you are on the `work` branch. Every instruction below is numbered in the exact order you should execute it. Do not skip a step.

---
## 1. Sync your branch
1. Open a terminal inside your repository folder.
2. Run `git fetch origin` so you can see the latest commits.
3. Switch to the working branch with `git checkout work`.
4. Pull the newest code with `git pull`. You should now be in sync with the remote repo before applying any edits.

---
## 2. Update `DoctorProfile.STATUS_CHOICES`
1. Open `mysite/booking/models.py` in your editor.
2. Find the `class DoctorProfile(models.Model):` definition near the top of the file.
3. Replace the entire `STATUS_CHOICES` list with the following block (copy/paste it exactly):
   ```python
   STATUS_CHOICES = [
       ("Pending", "Pending"),
       ("Approved", "Approved"),
       ("Rejected", "Rejected"),
       ("Active", "Active"),
       ("Inactive", "Inactive"),
   ]
   ```
4. Confirm that the `status` field inside `DoctorProfile` still reads `status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')`. Do not change the default or the `max_length`.

---
## 3. Add the `Appointment.datetime` helper
1. Still inside `mysite/booking/models.py`, scroll down until you see the `class Appointment(models.Model):` definition.
2. Delete any custom `__init__` method inside this class (there should not be one anymore).
3. Add the following property at the bottom of the `Appointment` class, right above the `Notification` model:
   ```python
   @property
   def datetime(self):
       """Return the appointment's timezone-aware datetime when possible."""
       if not self.date or not self.time:
           return None

       combined = datetime.combine(self.date, self.time)
       if timezone.is_naive(combined):
           try:
               return timezone.make_aware(combined)
           except Exception:
               # If the project is configured for naive datetimes just return the
               # combined value so the caller can still perform comparisons.
               return combined
       return combined
   ```
4. Save `models.py`. The file should now be identical to the version shown in `REFERENCE_FILES.md` (see Step 8).

---
## 4. Create migration `0007_alter_doctorprofile_status`
1. In the terminal, run `python manage.py makemigrations booking`.
2. Confirm Django creates `mysite/booking/migrations/0007_alter_doctorprofile_status.py`.
3. Open that migration file and ensure it matches the snippet in `REFERENCE_FILES.md`. The `choices` list must include all five statuses.

---
## 5. Update the `admin_doctors` view
1. Open `mysite/booking/views.py`.
2. Use the search feature in your editor to find the function named `admin_doctors`.
3. Replace the entire function with the version found in `REFERENCE_FILES.md`. This version:
   - Reads the `search` and `status` query parameters.
   - Uses `Q` objects to filter by doctor name, specialization, hospital, and city.
   - Applies a status filter when the dropdown is not set to `all`.
   - Orders the result by the doctor’s first name.
   - Returns the selected filters back to the template context via `search_query` and `status_filter`.
   - Keeps the activate/deactivate POST logic unchanged.
4. Save `views.py`.

---
## 6. Run migrations and automated tests
1. Apply the migration with `python manage.py migrate`.
2. Execute the test suite using `python manage.py test` (it will fail on this environment if Django is missing, but run it locally so you can confirm your setup works).

---
## 7. Review, stage, and commit
1. Run `git status` to verify the modified files are:
   - `mysite/booking/models.py`
   - `mysite/booking/views.py`
   - `mysite/booking/migrations/0007_alter_doctorprofile_status.py`
   - `mysite/booking/REFERENCE_FILES.md` (new helper file with copy-ready text)
2. Stage everything: `git add mysite/booking/models.py mysite/booking/views.py mysite/booking/migrations/0007_alter_doctorprofile_status.py mysite/booking/REFERENCE_FILES.md`
3. Commit with the message `Fix doctor statuses and admin filters`.

---
## 8. Copy-ready references
1. Open `mysite/booking/REFERENCE_FILES.md` for the full contents of every file mentioned above.
2. Copy each block into your editor if you prefer replacing entire files instead of editing line-by-line.
3. After copying, save the files again and repeat Step 6 to make sure everything still works.

Once all steps are complete, push your branch and open a pull request describing the work.
