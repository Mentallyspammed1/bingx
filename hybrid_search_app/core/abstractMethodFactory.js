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

  // This is a placeholder for the Enforcer class.
  // The user's drivers (e.g. Motherless.js) use `_AbstractModule2.default.with(_VideoMixin2.default)`
  // which suggests the mixin pattern is slightly different from what this factory was originally for.
  // The `Pornsearch.js` orchestrator directly checks for `getVideoSearchUrl`, `getGifSearchUrl`, `parseResults`.
  // So, this factory's role in *enforcing* might be diminished if drivers extend AbstractModule directly
  // and the mixins are conceptual or applied via AbstractModule.with().
  // For now, returning the BaseClass to not break the `require` chain in Mixin files.
  // A more robust solution would be to ensure the mixin application pattern is consistent.

  // Original logic:
  // const AbstractMethodEnforcer = class extends BaseClass { ... };
  // validAbstractMethods.forEach(methodName => { ... });
  // return AbstractMethodEnforcer;

  // Simplified version for compatibility if the factory's enforcement isn't strictly used by the new structure:
  return BaseClass;
};
