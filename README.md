![Pylo](https://github.com/user-attachments/assets/be096b09-00a0-40bc-893f-fd0158b258c6)

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/DiamondGotCat/Pylo) [![DGC-AutoBuild](https://github.com/DiamondGotCat/Pylo/actions/workflows/build.yml/badge.svg)](https://github.com/DiamondGotCat/Pylo/actions/workflows/build.yml)

# Pylo
Simple Programming Language

## Documentation
New Official Documentation is [here](https://pylo.diamondgotcat.net)!

## Example
```
# Save Result of 10 + 20 to "a" variable
var a: int = 10 + 20

# Save The remainder when a is divided by 7 to "b variable"
var b: int = mod(a, 7)

# Show Content
show("A is " + a)
show("B is " + b)

# Define Function named "add"
func add(x: int, y: int) -> int { # Define Input Args, and Return Contents.
    var result: int = x + y
    standard.output(conv.str(x) + " + " + conv.str(y) + " = " + result) # Show Content with Other Ways
}

# Call Function named "add"
add(5, 7)

# Execute Python from Pylo
exec.py("print(\"Hello, World!\")")
```
