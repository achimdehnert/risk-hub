#!/bin/bash
# Run this on the server: ssh root@88.198.191.108 < create_users.sh
# Or: scp create_users.sh root@88.198.191.108:/tmp/ && ssh root@88.198.191.108 "bash /tmp/create_users.sh"

# Cleanup build dir
rm -rf /tmp/risk-hub-build

# Load permissions
docker exec risk_hub_web python manage.py load_permissions

# List existing users
echo "=== Existing Users ==="
docker exec risk_hub_web python manage.py shell -c "
from identity.models import User
for u in User.objects.all():
    print(f'{u.id} | {u.username} | {u.email} | staff={u.is_staff} | super={u.is_superuser} | tenant={u.tenant_id}')
"

# Create superuser (admin)
echo "=== Creating superuser 'admin' ==="
docker exec risk_hub_web python manage.py shell -c "
from identity.models import User
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@schutztat.de', 'Schutztat2026!')
    u.first_name = 'System'
    u.last_name = 'Admin'
    u.save()
    print('Created superuser: admin / Schutztat2026!')
else:
    print('Superuser admin already exists')
"

# Create regular staff user
echo "=== Creating staff user 'achim' ==="
docker exec risk_hub_web python manage.py shell -c "
from identity.models import User
if not User.objects.filter(username='achim').exists():
    u = User.objects.create_user('achim', 'achim@schutztat.de', 'Schutztat2026!')
    u.first_name = 'Achim'
    u.last_name = 'Dehnert'
    u.is_staff = True
    u.save()
    print('Created staff user: achim / Schutztat2026!')
else:
    print('User achim already exists')
"

echo "=== Done ==="
echo ""
echo "Credentials:"
echo "  Superuser:  admin / Schutztat2026!  (admin@schutztat.de)"
echo "  Staff User: achim / Schutztat2026!  (achim@schutztat.de)"
echo ""
echo "Login: https://demo.schutztat.de/accounts/login/"
echo "Tenants: https://demo.schutztat.de/tenants/"
