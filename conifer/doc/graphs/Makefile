all: syrup-library.png syrup-item.png syrup.png syrup-user.png

syrup-library.png: syrup-library.dot
	dot -Tpng syrup-library.dot > syrup-library.png

syrup-user.png: syrup-user.dot
	dot -Tpng syrup-user.dot > syrup-user.png

syrup-item.png: syrup-item.dot
	dot -Tpng syrup-item.dot > syrup-item.png

syrup.png: syrup.dot
	fdp -Tpng syrup.dot > syrup.png
