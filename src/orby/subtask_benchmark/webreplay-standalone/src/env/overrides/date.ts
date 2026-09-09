/**
 * Creates a wrapper around the Date constructor to provide fixed time behavior
 * @param timestamp - The fixed timestamp to use
 * @returns A function that wraps the Date constructor to inject fixed time behavior
 */
export const createFixedDateConstructor = (timestamp: number): string => {
    // We return this as a string to be injected into the browser context
    return `
      // Store the original Date constructor
      const OriginalDate = Date;
      
      // Create a wrapper function that will replace the global Date constructor
      function FixedDate() {
        // If no arguments are provided, return a date based on our fixed timestamp
        if (arguments.length === 0) {
          return new OriginalDate(${timestamp});
        }
        
        // Otherwise, delegate to the original Date constructor
        // This preserves normal date handling for specific dates
        return new OriginalDate(...arguments);
      }
      
      // Copy all properties from the original Date constructor to our wrapper
      FixedDate.prototype = OriginalDate.prototype;
      FixedDate.now = function() { return ${timestamp}; };
      FixedDate.parse = OriginalDate.parse;
      FixedDate.UTC = OriginalDate.UTC;
      
      // Replace the global Date constructor with our wrapper
      Date = FixedDate;
    `;
  };
