extract:
	mkdir locales 
	pybabel extract --input-dirs=. -o locales/message.pot

init:
	pybabel init -i locales/message.pot -d locales -l eng 
	pybabel init -i locales/message.pot -d locales -l uz

compile:
	pybabel compile -d locales
	pybabel update -d locales -i locales/message.pot
	
update:
 	pybabel update -d locales -i locales/message.pot