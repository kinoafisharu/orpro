View [website](https://orpro-dev.herokuapp.com/)


On the local computer, all commands are executed together with `--settings=app.settings-run-local`

To create a backup data:
``` ./manage.py dumpdata --exclude auth.permission --exclude contenttypes > dump-filename.json ```