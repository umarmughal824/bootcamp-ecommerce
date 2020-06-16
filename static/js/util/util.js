// @flow
import Decimal from "decimal.js-light"
import * as R from "ramda"
import moment from "moment"

import { ORDER_FULFILLED } from "../constants"

/**
 * Creates a POST form with hidden input fields
 * @param url the url for the form action
 * @param payload Each key value pair will become an input field
 */
export function createForm(url: string, payload: Object): HTMLFormElement {
  const form = document.createElement("form")
  form.setAttribute("action", url)
  form.setAttribute("method", "post")
  form.setAttribute("class", "cybersource-payload")

  for (const key: string of Object.keys(payload)) {
    const value = payload[key]
    const input = document.createElement("input")
    input.setAttribute("name", key)
    input.setAttribute("value", value)
    input.setAttribute("type", "hidden")
    form.appendChild(input)
  }
  return form
}

export const isNilOrBlank = R.either(R.isNil, R.isEmpty)

export const formatDollarAmount = (amount: ?number): string => {
  amount = amount || 0
  const formattedAmount = amount.toLocaleString("en-US", {
    style:                 "currency",
    currency:              "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
  return formattedAmount.endsWith(".00") ?
    formattedAmount.substring(0, formattedAmount.length - 3) :
    formattedAmount
}

export const formatReadableDate = (datetime: moment$Moment): string =>
  datetime.format("MMM D, YYYY")

export const formatReadableDateFromStr = (datetimeString: string): string =>
  formatReadableDate(moment(datetimeString))

export const formatStartEndDateStrings = (
  startDtString: ?string,
  endDtString: ?string
): string => {
  let formattedStart, formattedEnd
  if (startDtString) {
    formattedStart = formatReadableDateFromStr(startDtString)
  }
  if (endDtString) {
    formattedEnd = formatReadableDateFromStr(endDtString)
  }
  if (!formattedStart && !formattedEnd) {
    return ""
  } else if (!formattedStart) {
    // $FlowFixMe: This cannot be un-initialized
    return `Ends ${formattedEnd}`
  } else if (!formattedEnd) {
    // $FlowFixMe: This cannot be un-initialized
    return `Starts ${formattedStart}`
  } else {
    return `${formattedStart} - ${formattedEnd}`
  }
}

export const getRunWithFulfilledOrder = (
  runData: ?Array<Object>,
  orderId: number
) =>
  R.find(
    bootcampRun =>
      R.any(
        payment =>
          payment.order.status === ORDER_FULFILLED &&
          payment.order.id === orderId,
        bootcampRun.payments
      ),
    runData
  )

export const getInstallmentDeadlineDates = R.map(
  R.compose(moment, R.prop("deadline"))
)

export function* incrementer(): Generator<number, *, *> {
  let int = 1
  // eslint-disable-next-line no-constant-condition
  while (true) {
    yield int++
  }
}

export const formatTitle = (text: string) => `MIT Bootcamps | ${text}`

export const newSetWith = (set: Set<*>, valueToAdd: any): Set<*> => {
  const newSet = new Set(set)
  newSet.add(valueToAdd)
  return newSet
}

export const newSetWithout = (set: Set<*>, valueToDelete: any): Set<*> => {
  const newSet = new Set(set)
  newSet.delete(valueToDelete)
  return newSet
}

/**
 * Returns a Promise that executes a function after a given number of milliseconds then resolves
 */
export const timeoutPromise = (
  funcToExecute: Function,
  timeoutMs: number
): Promise<*> => {
  return new Promise(resolve =>
    setTimeout(() => {
      funcToExecute()
      resolve()
    }, timeoutMs)
  )
}

export const formatPrice = (price: ?string | number | Decimal): string => {
  if (price === null || price === undefined) {
    return ""
  } else {
    let formattedPrice: Decimal = Decimal(price)

    if (formattedPrice.isInteger()) {
      formattedPrice = formattedPrice.toFixed(0)
    } else {
      formattedPrice = formattedPrice.toFixed(2, Decimal.ROUND_HALF_UP)
    }
    return `$${formattedPrice}`
  }
}

export const getFilenameFromPath = (url: string) =>
  url.substring(url.lastIndexOf("/") + 1)
