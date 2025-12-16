/**
 * JavaScript file with ES6 classes and methods.
 */

class Animal {
  constructor(name) {
    this.name = name;
  }

  speak() {
    console.log(`${this.name} makes a sound.`);
  }
}

class Dog extends Animal {
  constructor(name, breed) {
    super(name);
    this.breed = breed;
  }

  speak() {
    console.log(`${this.name} barks.`);
  }

  fetch() {
    return "Fetching ball!";
  }
}

function createAnimal(name) {
  return new Animal(name);
}

export { Animal, Dog, createAnimal };
