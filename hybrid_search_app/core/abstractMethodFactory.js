// core/abstractMethodFactory.js
'use strict';
const OverwriteError = require('./OverwriteError');

module.exports = (BaseClass, abstractMethods) => {
  if (typeof BaseClass !== 'function' || !BaseClass.prototype) { // Added prototype check
    throw new Error('BaseClass must be a constructor function (a class).');
  }

  if (!Array.isArray(abstractMethods)) { // Removed length check, empty array is valid
    throw new Error('The second argument "abstractMethods" must be an array of strings.');
  }

  const validAbstractMethods = abstractMethods.filter(methodName =>
    typeof methodName === 'string' && methodName.trim().length > 0
  );

  // It's okay if validAbstractMethods is empty, means the mixin is just a marker or adds concrete methods.

  const AbstractMethodEnforcer = class extends BaseClass {
    constructor(...args) {
      super(...args); // This calls the constructor of BaseClass (e.g., AbstractModule or a class already mixed)

      // Optional: Runtime check for method implementation on the instance.
      // This is more for ensuring the final driver implements them.
      // The prototype stubs below handle the "abstract" nature.
      validAbstractMethods.forEach(methodName => {
        if (typeof this[methodName] !== 'function') {
            // This check is tricky because methods are on prototype.
            // The main enforcement is calling the stub if not overridden.
        }
      });
    }
  };

  validAbstractMethods.forEach(methodName => {
    // Define methods on the prototype that throw if not overridden by a concrete subclass
    // This ensures that if a driver uses a mixin, it must implement these methods.
    if (typeof AbstractMethodEnforcer.prototype[methodName] === 'undefined') {
      Object.defineProperty(AbstractMethodEnforcer.prototype, methodName, {
        value: function() {
          const callingClassName = this.constructor.name || 'Subclass';
          throw new OverwriteError(
            `Abstract method "${methodName}" from mixin must be implemented by concrete class "${callingClassName}".`
          );
        },
        writable: true, // Allows subclasses to override
        configurable: true,
        enumerable: false,
      });
    }
  });

  return AbstractMethodEnforcer; // Return the new class that extends BaseClass
};
