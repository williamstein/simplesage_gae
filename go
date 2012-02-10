sleep 3 && open http://localhost:9000 &

echo "Start the worker with 'sage worker.py'"

dev_appserver.py . -p 9000
