# YPSH Language's Syntax

## Comments
Syntax for add strings in your code that you don't want to affect execution

```ypsh
# one-line comment with sharp
// other ways to one-line comment, with two slash
/*
multi-line comment with slash and asterisk
*/
```

## Variables
Syntax for temporarily storing values

**Variable declaration (var):**
Declares a variable that can be reassigned.
```ypsh
var name = "Alice"
var age: int = 30
name = "Bob"
```

**Constant declaration (let):**
Declares a read-only variable that cannot be changed once assigned.
```ypsh
let birth_year = 1990
```

**Assignment:**
Assign a value to a variable.
```ypsh
var x = 50
x = 100
```

**Compound Assignment Operators:**
Performs calculation and assignment simultaneously.
```ypsh
var score = 10
score += 5
score -= 2
score *= 3
score /= 3
```

**Scope:**
Specifies whether the variable belongs to the global or local scope.
```ypsh
global var global_var = "I'm global"
func my_func() {
    local var local_var = "I'm local"
}
```

## Data Types and Literals
Way to write values ​​that can be directly handled in a program

**Number:**
Integers and floating point numbers are available.
```ypsh
let integer = 42
let floating_point = 3.14
```

**String:**
Enclose it in single quotes (`'`) or double quotes (`"`). Multi-line strings are also possible.
```ypsh
let single = 'hello'
let double = "world"
let multi_line = """
This is a
multi-line string.
"""
```

**String Interpolation:**
You can embed expressions in strings, using the format `\(...)`.
```ypsh
let name = "YPSH"
let greeting = "Hello, \(name)!"
```

**List:**
An ordered collection of values.
```ypsh
let my_list = [1, "apple", true, [10, 20]]
```

**Dict:**
A collection of key-value pairs, where the keys are strings or IDs.
```ypsh
let my_dict = {
    "name": "Alice",
    age: 30,
    "is_active": True
}
```

**Bool:**
`True`(or `true`) and `False`(or false)

**None:**
`None`(or `none`)

## Operators

**Arithmetic operators (four arithmetic operations):**
`+`, `-`, `*` and `/`

**Comparison operators:**
`==`, `!=`, `<`, `>`, `<=`, `>=`

**Logical operators:**
`&&`, `||`, `!`

**Ternary operator:**
`condition ? value_if_true : value_if_false`
```ypsh
let max_val = a > b ? a : b
```

**Attribute Access:**
Access the attribute of an object.
```ypsh
let version = ypsh.version
```

**Index Access:**
Accesses elements of a list or dictionary.
```ypsh
let first_item = my_list[0]
let user_name = my_dict["name"]
```

## Control statements
Control the flow of program execution.

**`if-elif-else` statement:**
Branches processing depending on conditions.
```ypsh
if score == 100 {
    print("Perfect!")
} elif score >= 80 {
    print("Great.")
} else if score >= 50 {
    print("Good.")
} else {
    print("Needs improvement.")
}
```

**`switch` statement:**
Branches processing depending on the value of the expression.
```ypsh
switch status_code {
    case 200: {
        print("OK")
    }
    case 404: {
        print("Not Found")
    }
    default: {
        print("Unknown status")
    }
}
```

**`for` loop:**
Iterates over the elements of an iterable object, such as a list.
```ypsh
for fruit in ["apple", "banana", "cherry"] {
    print(fruit)
}
```

**`while` loop:**
Repeats the process while the condition is `True`.
```ypsh
var count = 0
while count < 3 {
    print(count)
    count += 1
}
```

**Loop Control:**
- `break`: Break the loop.
- `continue`: Skip the current iteration and go to the next iteration.

## Functions
It is a collection of processes.

**Function definition:**
```ypsh
func greet(name: str, greeting = "Hello") -> str {
    let message = "\((greeting)), \((name))!"
    return message
}
```

**`return` statement:**
Returns a value from a function.

**Function calls**
```ypsh
let msg = greet("World")
cprint(greet(name="YPSH", greeting="Hi"))
```

## Object Oriented
**Template (`template`):**
It's like a blueprint for a class, it defines its properties and methods.
```ypsh
template PersonTemplate {
    var name = "Unknown"
    func say_hello() {
        print("Hello, I'm \((self.name))")
    }
}
```

**Class (`class`):**
Defines a concrete class. Templates can be inherited.
```ypsh
class User: PersonTemplate {
    func __init__(self, user_name) {
        self.name = user_name
    }
}

let user1 = User("Alice")
user1.say_hello()
```

## Enumerations (Enum)
Defines a group of related values.
```
enum Signal {
    case RED, YELLOW, GREEN
}

let current_signal = Signal.GREEN

if current_signal == Signal.GREEN {
    print("Go!")
}
```

## Exception Handling
Safely execute code that may encounter errors.
```ypsh
do {
    let result = 10 / 0
} catch err {
    print("An error occurred: \(err)")
}
```

## Shell Commands
It is executed in a subprocess as an OS shell command.
```ypsh
$ ls -l /tmp
$ echo "Hello from shell"
```

## Other
- **Blocks (`{...}`):** Group multiple statements together using constructs like `if`, `for`, `func`, etc.
- **Semicolons (`;`):** Can indicate the end of a statement, but are often optional.
