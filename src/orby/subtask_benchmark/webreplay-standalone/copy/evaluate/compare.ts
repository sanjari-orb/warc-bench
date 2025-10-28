import * as diff from 'diff';
import { isEqual } from 'lodash';
import { Action } from 'protos/pb/v1alpha1/orbot_action';
import { logger } from '../libs/logger';
import { ElementLocator } from 'protos/pb/v1alpha1/element';

/**
 * Compare the generated {@link Action}s with the actions specified in the
 * {@link Replay} message.
 */
export function compareGeneratedActions(
  expected: Action[],
  generated: Action[],
): boolean {
  if (expected.length !== generated.length) {
    logger.error(
      `Generated ${generated.length} actions while we are expecting ${expected.length}`,
    );
    logger.diff(diff.diffJson(generated, expected));
    return false;
  }

  for (let i = 0; i < expected.length; i++) {
    const action = expected[i]!;
    const generatedAction = generated[i]!;
    if (action.foreach) {
      if (!generatedAction.foreach) {
        logger.error(
          `Expect a foreach action, but got ${JSON.stringify(generatedAction)}`,
        );
        return false;
      }
      if (
        !compareActions(
          action.foreach.loopActions!,
          generatedAction.foreach.loopActions!,
        )
      ) {
        return false;
      }
    } else if (action.condition || generatedAction.condition) {
      logger.error('condition action is not supported yet');
      return false;
    } else {
      if (!compareAction(action, generatedAction)) {
        return false;
      }
    }
  }
  return true;
}

function compareActions(a: Action[], b: Action[]) {
  if (a.length !== b.length) {
    logger.error(
      `Generated ${b.length} actions while we are expecting ${a.length}`,
    );
    logger.diff(diff.diffJson(a, b));
    return false;
  }
  for (let i = 0; i < a.length; i++) {
    if (!compareAction(a[i]!, b[i]!)) {
      return false;
    }
  }
  return true;
}

/**
 * Compare {@link Action}s equality ignoring description, id and reference params.
 */
function compareAction(a: Action, b: Action) {
  // make a copy of the PreparedAction
  const actionA = Action.create(a);
  const actionB = Action.create(b);

  // clear non-relevant fields
  actionA.id = undefined;
  actionB.id = undefined;
  actionA.elementIds = [];
  actionB.elementIds = [];
  actionA.rawEvents = [];
  actionB.rawEvents = [];
  actionA.description = undefined;
  actionB.description = undefined;
  actionA.observedAt = undefined;
  actionB.observedAt = undefined;
  actionA.completedAt = undefined;
  actionB.completedAt = undefined;
  actionA.verification = undefined;
  actionB.verification = undefined;
  actionA.useDebugger = undefined;
  actionB.useDebugger = undefined;

  // clear reference params
  normalizeParams(actionA);
  normalizeParams(actionB);
  if (!isEqual(actionA, actionB)) {
    const changes = diff.diffJson(actionA, actionB);
    logger.error('Actions not equal: ');
    logger.diff(changes);
    return false;
  }
  return true;
}

/**
 * All 'jsonValue' properties will be converted to json object
 */
function normalizeParams(action: Action) {
  // Recursively process all properties of the action
  for (const key in action) {
    const value = action[key as keyof Action];

    if (value && typeof value === 'object') {
      // Handle arrays
      if (Array.isArray(value)) {
        value.forEach((item) => {
          if (item && typeof item === 'object') {
            normalizeParams(item as Action);
          }
        });
      } else {
        // Handle nested objects
        normalizeParams(value as Action);
      }
    }

    // Convert jsonValue if found
    if (key === 'jsonValue' && typeof value === 'string') {
      try {
        // This is a hack to better visualize the diff
        const parsedValue = JSON.parse(value);
        // Clear non-relevant fields in jsonValue and parentLocator
        if (typeof parsedValue === 'object') {
          clearLocatorFields(parsedValue);
        }
        (action as any)[key] = ElementLocator.create(parsedValue);
      } catch (e) {
        logger.error(`Failed to parse jsonValue: ${value}`);
        // Keep original value if parsing fails
      }
    }

    // Remove referenceValue for now
    if (key === 'referenceValue') {
      (action as any)[key] = undefined;
    }
  }
}

function clearLocatorFields(locator: ElementLocator) {
  if (!locator) return;
  locator.elementId = '';
  locator.name = '';
  if (locator.parentLocator) {
    clearLocatorFields(locator.parentLocator);
  }
}
