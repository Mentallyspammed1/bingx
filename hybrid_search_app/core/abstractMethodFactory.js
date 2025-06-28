// core/abstractMethodFactory.js
'use strict';
const OverwriteError = require('./OverwriteError'); // Correct path

module.exports = (BaseClass, abstractMethods) => {
  if (typeof BaseClass !== 'function') {
    throw new Error('BaseClass must be a constructor function.');
  }

  if (!Array.isArray(abstractMethods) || abstractMethods.length === 0) {
    throw new Error('The second argument "abstractMethods" must be a non-empty array of strings.');
  }

  const validAbstractMethods = abstractMethods.filter(methodName =>
    typeof methodName === 'string' && methodName.trim().length > 0
  );

  if (validAbstractMethods.length === 0) {
    throw new Error('After filtering invalid entries, the "abstractMethods" array is empty or contains only invalid method names.');
  }

  const AbstractMethodEnforcer = class extends BaseClass {
    constructor(...args) {
      super(...args);
    }
  };

  validAbstractMethods.forEach(methodName => {
    Object.defineProperty(AbstractMethodEnforcer.prototype, methodName, {
      get() {
        // This getter is invoked when the 'abstract' method is accessed.
        // It returns the function that will actually be called.
        return (...args) => { // eslint-disable-line no-unused-vars
          // 'this' here refers to the instance of the concrete subclass.
          const callingClassName = this.constructor.name || 'Subclass';
          throw new OverwriteError(
            `Abstract method "${methodName}" must be implemented by concrete class "${callingClassName}".`
          );
        };
      },
      configurable: true, // Allows subclasses to override.
      enumerable: false,   // Keeps it off for...in loops on the prototype.
    });
  });

  return AbstractMethodEnforcer;
};
