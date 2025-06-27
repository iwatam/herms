import herms.tag as t

def test_tag_config():
    tags= list(t.Tag.configure({"foo":"bar","baz":"qux"}))
    assert tags[0].name=="foo"
    assert tags[0].description=="bar"
    assert tags[1].name=="baz"
    assert tags[1].description=="qux"

    tags= list(t.Tag.configure(["t1","t2"]))
    assert tags[0].name=="t1"
    assert tags[1].name=="t2"

    tags= list(t.Tag.configure({"t3":{"description":"d3","abstract":True,"children":["t31","t32"]},"t4":"d4"}))
    assert tags[0].name=="t3"
    assert tags[0].description=="d3"
    assert tags[0].abstract
    assert tags[0].children["t31"].name=="t31"
    assert tags[0].children["t32"].name=="t32"
    assert tags[1].name=="t4"
    assert tags[1].description=="d4"
