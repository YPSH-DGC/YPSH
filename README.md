# Pylo - Simple Programming Language

## Links
- [Pylo Docs](https://diamondgotcat.gitbook.io/pylo/): All the features and functions are listed here

## Requirements
- Python 3.6+
    - `rich` Library
    - `requests` Library (for `https` module)

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

## Loop Control

`break` exits the nearest loop and `continue` skips to the next iteration.

```pylo
var i = 0
while (true) {
    i = i + 1
    if (i == 2) {
        continue
    }
    show(i)
    if (i > 3) {
        break
    }
}
```

## Logical Operators

Boolean expressions support `&&`, `||` and `!`.

```pylo
if (true && !false) {
    show("logic works")
}
```
