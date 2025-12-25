#![deny(clippy::all)]

use napi_derive::napi;

// =============================================================================
// Simple Functions
// =============================================================================

/// Add two numbers
#[napi]
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

/// Greet someone
#[napi]
pub fn greet(name: String) -> String {
    format!("Hello, {}!", name)
}

/// Return a constant
#[napi]
pub fn get_magic_number() -> i32 {
    42
}

// =============================================================================
// Objects
// =============================================================================

/// Create a simple object with fields
#[napi(object)]
pub struct Person {
    pub name: String,
    pub age: u32,
}

/// Create a person object
#[napi]
pub fn create_person(name: String, age: u32) -> Person {
    Person { name, age }
}

/// Get person info as string
#[napi]
pub fn describe_person(person: Person) -> String {
    format!("{} is {} years old", person.name, person.age)
}

// =============================================================================
// Callbacks
// =============================================================================

/// Call a callback with a value
#[napi]
pub fn call_with_value(callback: napi::bindgen_prelude::Function<i32, i32>, value: i32) -> napi::Result<i32> {
    callback.call(value)
}

/// Apply a callback to each element and return sum
#[napi]
pub fn map_and_sum(numbers: Vec<i32>, callback: napi::bindgen_prelude::Function<i32, i32>) -> napi::Result<i32> {
    let mut sum = 0;
    for n in numbers {
        let result = callback.call(n)?;
        sum += result;
    }
    Ok(sum)
}

// =============================================================================
// Arrays
// =============================================================================

/// Double each element in array
#[napi]
pub fn double_array(numbers: Vec<i32>) -> Vec<i32> {
    numbers.into_iter().map(|n| n * 2).collect()
}

/// Get array length
#[napi]
pub fn array_length(arr: Vec<i32>) -> u32 {
    arr.len() as u32
}

// =============================================================================
// Class
// =============================================================================

/// A simple counter class
#[napi]
pub struct Counter {
    value: i32,
}

#[napi]
impl Counter {
    #[napi(constructor)]
    pub fn new(initial: Option<i32>) -> Self {
        Counter {
            value: initial.unwrap_or(0),
        }
    }

    /// Increment the counter
    #[napi]
    pub fn increment(&mut self) {
        self.value += 1;
    }

    /// Decrement the counter
    #[napi]
    pub fn decrement(&mut self) {
        self.value -= 1;
    }

    /// Add a value to the counter
    #[napi]
    pub fn add(&mut self, n: i32) {
        self.value += n;
    }

    /// Get current value
    #[napi(getter)]
    pub fn value(&self) -> i32 {
        self.value
    }

    /// Set value
    #[napi(setter)]
    pub fn set_value(&mut self, value: i32) {
        self.value = value;
    }

    /// Reset to zero
    #[napi]
    pub fn reset(&mut self) {
        self.value = 0;
    }
}

// =============================================================================
// Error handling
// =============================================================================

/// Function that may fail
#[napi]
pub fn divide(a: i32, b: i32) -> napi::Result<i32> {
    if b == 0 {
        return Err(napi::Error::from_reason("Division by zero"));
    }
    Ok(a / b)
}

// =============================================================================
// Optional/Nullable
// =============================================================================

/// Return None if negative, Some otherwise
#[napi]
pub fn maybe_double(n: i32) -> Option<i32> {
    if n < 0 {
        None
    } else {
        Some(n * 2)
    }
}

/// Accept optional parameter
#[napi]
pub fn greet_optional(name: Option<String>) -> String {
    match name {
        Some(n) => format!("Hello, {}!", n),
        None => "Hello, stranger!".to_string(),
    }
}

// =============================================================================
// Async / Promises
// =============================================================================

/// Simple async function - returns after a delay
#[napi]
pub async fn async_add(a: i32, b: i32) -> i32 {
    // Simulate some async work
    a + b
}

/// Async function with delay (uses tokio sleep internally via napi-rs)
#[napi]
pub async fn delayed_value(value: i32, ms: u32) -> i32 {
    // napi-rs handles the async runtime
    tokio::time::sleep(std::time::Duration::from_millis(ms as u64)).await;
    value
}

/// Async function that may fail
#[napi]
pub async fn async_divide(a: i32, b: i32) -> napi::Result<i32> {
    if b == 0 {
        return Err(napi::Error::from_reason("Division by zero"));
    }
    Ok(a / b)
}

/// Async function that processes an array
#[napi]
pub async fn async_sum(numbers: Vec<i32>) -> i32 {
    numbers.iter().sum()
}
