IMAGES=$(patsubst %.tex,%.png,$(wildcard *.tex))

%.pdf: %.tex
	pdflatex $< -output-directory=$@

%.png: %.pdf
	convert -flatten -density 300 -trim -quality 100 $< $@

images: $(IMAGES)
	rm -r -f *.pdf *.aux *.log
