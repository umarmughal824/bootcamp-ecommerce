import { assert } from "chai"
import moment from "moment"
import _ from "lodash"

import {
  generateFakePayableRuns,
  generateFakeInstallment,
  generateFakeRun
} from "../factories"
import {
  createForm,
  isNilOrBlank,
  formatDollarAmount,
  formatRunDateRange,
  getRunWithFulfilledOrder,
  getInstallmentDeadlineDates,
  formatPrice,
  formatStartEndDateStrings,
  newSetWithout,
  newSetWith,
  getFilenameFromPath,
  getFilenameFromMediaPath,
  isErrorResponse,
  parsePrice,
  transformError
} from "./util"

import type { HttpResponse } from "../flow/httpTypes"
import { CS_101, CS_102, CS_DEFAULT, CS_ERROR_MESSAGES } from "../constants"

describe("util", () => {
  describe("createForm", () => {
    it("creates a form with hidden values corresponding to the payload", () => {
      const url = "url"
      const payload = { pay: "load" }
      const form = createForm(url, payload)

      const clone = { ...payload }
      for (const hidden of form.querySelectorAll("input[type=hidden]")) {
        const key = hidden.getAttribute("name")
        const value = hidden.getAttribute("value")
        assert.equal(clone[key], value)
        delete clone[key]
      }
      // all keys exhausted
      assert.deepEqual(clone, {})
      assert.equal(form.getAttribute("action"), url)
      assert.equal(form.getAttribute("method"), "post")
    })
  })

  describe("isNilOrBlank", () => {
    it("returns true for undefined, null, and a blank string", () => {
      [undefined, null, ""].forEach(value => {
        assert.isTrue(isNilOrBlank(value))
      })
    })

    it("returns false for a non-blank string", () => {
      assert.isFalse(isNilOrBlank("not blank"))
    })
  })

  describe("formatDollarAmount", () => {
    it("returns a properly formatted dollar value", () => {
      [undefined, null].forEach(nilValue => {
        assert.equal(formatDollarAmount(nilValue), "$0")
      })
      assert.equal(formatDollarAmount(100), "$100")
      assert.equal(formatDollarAmount(100.5), "$100.50")
      assert.equal(formatDollarAmount(10000), "$10,000")
      assert.equal(formatDollarAmount(100.12), "$100.12")
    })
  })

  describe("getRunWithFulfilledOrder", () => {
    let bootcampRuns, bootcampRun

    beforeEach(() => {
      bootcampRuns = generateFakePayableRuns(1, { hasPayment: true })
      bootcampRun = bootcampRuns[0]
    })

    it("gets a fulfilled order from the payments in the bootcamp runs", () => {
      bootcampRun.payments[0].order.status = "fulfilled"
      assert.deepEqual(
        getRunWithFulfilledOrder(
          bootcampRuns,
          bootcampRun.payments[0].order.id
        ),
        bootcampRun
      )
    })

    it("returns undefined if the order doesn't exist", () => {
      bootcampRun.payments[0].order.status = "fulfilled"
      assert.deepEqual(getRunWithFulfilledOrder(bootcampRuns, 9999), undefined)
    })

    it("returns undefined if the order is not fulfilled", () => {
      bootcampRun.payments[0].order.status = "created"
      assert.deepEqual(
        getRunWithFulfilledOrder(
          bootcampRuns,
          bootcampRun.payments[0].order.id
        ),
        undefined
      )
    })
  })

  describe("getInstallmentDeadlineDates", () => {
    it("returns a list of parsed deadline dates when given an array of installment data", () => {
      const moments = [
        moment({ milliseconds: 0 }),
        moment({ milliseconds: 0 }).add(5, "days")
      ]
      const installments = [
        generateFakeInstallment({ deadline: moments[0].format() }),
        generateFakeInstallment({ deadline: moments[1].format() })
      ]
      // Assert that the arrays of dates are equivalent (using this approach since moment objects
      // store a bunch of extra properties that make assert.deepEqual unusable)
      _.each(getInstallmentDeadlineDates(installments), (installment, i) => {
        assert.isTrue(installment.isSame(moments[i]))
      })
    })
  })

  describe("formatStartEndDateStrings", () => {
    it("should format correctly when two date strings are provided", () => {
      const datetimes = [
        moment({ milliseconds: 0 }),
        moment({ milliseconds: 0 }).add(5, "days")
      ]
      const result = formatStartEndDateStrings(
        datetimes[0].format(),
        datetimes[1].format()
      )
      assert.deepEqual(
        result,
        `${datetimes[0].format("MMM D, YYYY")} - ${datetimes[1].format(
          "MMM D, YYYY"
        )}`
      )
    })

    it("should format correctly when only a start date is provided", () => {
      const dt = moment()
      const result = formatStartEndDateStrings(dt.format(), null)
      assert.deepEqual(result, `Starts ${dt.format("MMM D, YYYY")}`)
    })

    it("should format correctly when only an end date is provided", () => {
      const dt = moment()
      const result = formatStartEndDateStrings(null, dt.format())
      assert.deepEqual(result, `Ends ${dt.format("MMM D, YYYY")}`)
    })

    it("should return an empty string when no dates are provided", () => {
      const result = formatStartEndDateStrings(null, null)
      assert.deepEqual(result, "")
    })
  })

  it("newSetWith returns a set with an additional item", () => {
    const set = new Set([1, 2, 3])
    assert.deepEqual(newSetWith(set, 3), set)
    assert.deepEqual(newSetWith(set, 4), new Set([1, 2, 3, 4]))
  })

  it("newSetWithout returns a set without a specified item", () => {
    const set = new Set([1, 2, 3])
    assert.deepEqual(newSetWithout(set, 3), new Set([1, 2]))
    assert.deepEqual(newSetWithout(set, 4), set)
  })

  //
  ;["https://a/b/c/de/f/g.html", "https://g.html", "g.html"].forEach(url => {
    it(`getFilenameFromPath extracts 'g.html' from path ${url}`, () => {
      assert.equal(getFilenameFromPath(url), "g.html")
    })
  })

  //
  ;[
    ["media/1/1-2-3-4_resume_1_2_3.pdf", "resume_1_2_3.pdf"],
    ["media/1/1-2-3-4_resume.pdf", "resume.pdf"],
    ["", ""],
    [undefined, ""]
  ].forEach(([path, expResult]) => {
    it(`getFilenameFromMediaPath extracts file name from media path ${path}`, () => {
      assert.equal(getFilenameFromMediaPath(path), expResult)
    })
  })

  //
  ;[
    [200, false],
    [299, false],
    [300, false],
    [400, true],
    [500, true]
  ].forEach(([status, expResult]) => {
    it(`isErrorResponse returns ${String(expResult)} when status=${String(
      status
    )}`, () => {
      const response: HttpResponse<*> = {
        status: status,
        body:   {}
      }
      assert.equal(isErrorResponse(response), expResult)
    })
  })

  describe("formatPrice", () => {
    it("format price", () => {
      assert.equal(formatPrice(20), "$20")
      assert.equal(formatPrice(20.005), "$20.01")
      assert.equal(formatPrice(20.1), "$20.10")
      assert.equal(formatPrice(20.6059), "$20.61")
      assert.equal(formatPrice(20.6959), "$20.70")
      assert.equal(formatPrice(20.1234567), "$20.12")
      assert.equal(formatPrice(-0.0000000001), "$0")
      assert.equal(formatPrice(-123.467), "-$123.47")
    })

    it("returns an empty string if null or undefined", () => {
      assert.equal(formatPrice(null), "")
      assert.equal(formatPrice(undefined), "")
    })
  })

  describe("parsePrice", () => {
    it("parses a price to a Decimal, rounding to the nearest cent", () => {
      assert.equal(parsePrice("0.00000001").toString(), "0")
    })

    it("returns null if the string is not parsable", () => {
      assert.isNull(parsePrice("notaprice"))
    })
  })

  const TEST_DATE = "2020-05-01"
  describe("start and end dates", () => {
    [
      [
        moment(TEST_DATE).format(),
        moment(TEST_DATE)
          .add(1, "days")
          .format(),
        "mai 1, 2020 - mai 2, 2020"
      ],
      [moment(TEST_DATE).format(), null, "mai 1, 2020 - TBD"],
      [
        null,
        moment(TEST_DATE)
          .add(1, "days")
          .format(),
        "TBD - mai 2, 2020"
      ],
      [null, null, "TBD - TBD"]
    ].forEach(([startDate, endDate, expectedText]) => {
      it(`renders bootcamp dates where startDate=${String(
        startDate
      )} and endDate=${String(endDate)}`, async () => {
        const run = {
          ...generateFakeRun(),
          start_date: startDate,
          end_date:   endDate
        }
        assert.equal(formatRunDateRange(run), expectedText)
      })
    })
  })

  //
  ;[
    ["CS_101", CS_ERROR_MESSAGES[CS_101]],
    ["CS_102", CS_ERROR_MESSAGES[CS_102]],
    ["CS_150", CS_ERROR_MESSAGES[CS_DEFAULT]],
    ["FOO", CS_ERROR_MESSAGES[CS_DEFAULT]]
  ].forEach(([errorCode, errorMsg]) => {
    it(`transformError returns '${errorMsg}' for error code '${errorCode}'`, () => {
      assert.equal(transformError(errorCode), errorMsg)
    })
  })
})
