import spacy

nlp = spacy.load("es_core_news_md")
print("Modelo cargado:", nlp.meta["lang"], "-", nlp.meta["version"])

doc = nlp("Hola, me llamo Darwin y estoy probando spaCy.")
print([(token.text, token.pos_) for token in doc])
