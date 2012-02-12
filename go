sleep 3 && open http://localhost:9000 &

echo "You must manually start the worker with 'sage worker.py http://localhost:9000'"

echo "Uses './go -c' if you want to reset the entire database."

dev_appserver.py . -p 9000 $@
