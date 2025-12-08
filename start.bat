@echo off

start cmd /k "instatunnel connect 10100 --subdomain barcarolograziadei-payment"
:start cmd /k "python Payments/payment_service.py"

::start cmd /k "instatunnel connect 5000 --subdomain barcarolograziadei-authentication"
start cmd /k "python telegram_bot.py"
start cmd /k "python Authentication/authentication_service.py"

echo "System started."