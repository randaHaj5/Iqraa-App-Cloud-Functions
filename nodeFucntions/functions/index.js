
const functions = require("firebase-functions");
const _ = require("lodash");
// The Firebase Admin SDK to access Firestore.
const admin = require("firebase-admin");
const {firestore} = require("firebase-admin");
const series = require("async/series");
const parallel = require("async/parallel");
const {isEmpty} = require("lodash");
admin.initializeApp();
exports.sendPublicNotification = functions.https.onRequest(
    (request, response) => {
      response.send(request.body);
      console.log("~~~Sending public notification");
      const newBody = JSON.parse(request.body);
      const title = newBody.title;
      const tokens = newBody.tokens;
      const body = newBody.body;
      const message = {
        notification: {
          title: title,
          body: body,
        },
        data: {
          title: title,
          body: body,
        },
      };
      admin
          .messaging()
          .sendToDevice(tokens, message)
          .then((response) => {
            // Response is a message ID string.
            console.log("Successfully sent message:", response);
          })
          .catch((error) => {
            console.log("Error sending message:", error);
          });
    }
);
/**
 * to post tracking record
 * @param {string} id user id
 * @param {object} data tracking object
 * @return {int} The res
 */
function postOneTracking(id, data) { // test
  const db = admin.firestore();
  return new Promise((resolve, reject) => {
    if (data && !_.isEmpty(data)) {
      db.collection("Tracking")
          .doc(id)
          .set(data)
          .then((res) => {
            resolve();
          })
          .catch((err) => {
            reject(new Error(err));
          });
    } else resolve();
  });
}
/**
 * to post bookmark record
 * @param {string} id user id
 * @param {object} data bookmark object
 * @return {int} The res
 */
function postOneBookmark(id, data) {
  const db = admin.firestore();
  return new Promise((resolve, reject) => {
    if (data && !_.isEmpty(data)) {
      db.collection("bookmarks")
          .doc(id)
          .set(data)
          .then((res) => {
            resolve();
          })
          .catch((err) => {
            reject(new Error(err));
          });
    } else resolve();
  });
}
/**
 * to post note record
 * @param {string} id user id
 * @param {object} data note object
 * @return {int} The res
 */
function postOneNote(id, data) {
  const db = admin.firestore();
  return new Promise((resolve, reject) => {
    if (data && !_.isEmpty(data)) {
      db.collection("notes")
          .doc(id)
          .set(data)
          .then((res) => {
            resolve();
          })
          .catch((err) => {
            reject(new Error(err));
          });
    } else resolve();
  });
}
exports.uploadUsersData = functions.https.onRequest((request, response) => {
  const notes = request.query.notes;
  const bookmarks = request.query.bookmarks;
  const tracking = request.query.tracking;
  const notesData = JSON.parse(notes);
  const bookmarksData = JSON.parse(bookmarks);
  const trackingData = JSON.parse(tracking);
  const requestsToExecute = _.map(trackingData, (oneTracking) => {
    return (callBack) => {
      postOneTracking(oneTracking.id, oneTracking.data)
          .then((res) => {
            callBack(null, res);
          })
          .catch((err) => {
            callBack(null, {});
          });
    };
  });
  const bookmarksRequestsToExecute = _.map(bookmarksData, (oneBookmark) => {
    return (callBack) => {
      postOneBookmark(oneBookmark.id, oneBookmark.data)
          .then((res) => {
            callBack(null, res);
          })
          .catch((err) => {
            callBack(null, {});
          });
    };
  });
  const NotesRequestsToExecute = _.map(notesData, (oneNote) => {
    return (callBack) => {
      postOneNote(oneNote.id, oneNote.data)
          .then((res) => {
            callBack(null, res);
          })
          .catch((err) => {
            callBack(null, {});
          });
    };
  });
  series(
      _.concat(
          requestsToExecute,
          NotesRequestsToExecute,
          bookmarksRequestsToExecute
      ),
      function(err, results) {
        response.send({Success: "Done--------------"});
      }
  );
});

exports.getUsersData = functions.https.onRequest((request, response) => {
  const profileIds = request.query.profileIds;
  const userId = request.query.userId;
  const db = admin.firestore();

  const bookmarksRefs = [];
  const trackingRefs = [];
  const notesRefs = [];
  _.map(JSON.parse(profileIds), (oneId) => {
    bookmarksRefs.push(firestore().doc(`bookmarks/${oneId}`));
    notesRefs.push(db.doc(`notes/${oneId}`));
    trackingRefs.push(db.doc(`Tracking/${oneId}`));
  });
  parallel(
      [
        (callback) => {
          if (bookmarksRefs && !isEmpty(bookmarksRefs)) {
            db.getAll(...bookmarksRefs)
                .then((bookmarksDocs) => {
                  const bookmarksDataToSend = {};
                  _.map(bookmarksDocs, (oneDoc) => {
                    if (oneDoc && oneDoc.data()) {
                      bookmarksDataToSend[oneDoc.id] = {data: oneDoc.data()};
                    }
                  });
                  callback(null, bookmarksDataToSend);
                })
                .catch(() => callback());
          } else callback(null, {});
        },
        (callback) => {
          if (notesRefs && !isEmpty(notesRefs)) {
            db.getAll(...notesRefs)
                .then((notesDocs) => {
                  const noteDataToSend = {};
                  _.map(notesDocs, (oneDoc) => {
                    if (oneDoc && oneDoc.data()) {
                      noteDataToSend[oneDoc.id] = {data: oneDoc.data()};
                    }
                  });
                  callback(null, noteDataToSend);
                })
                .catch(() => callback());
          } else callback(null, {});
        },
        (callback) => {
          if (notesRefs && !isEmpty(notesRefs)) {
            db.getAll(...trackingRefs)
                .then((trackingDocs) => {
                  const trackingDataToSend = {};
                  _.map(trackingDocs, (oneDoc) => {
                    if (oneDoc && oneDoc.data()) {
                      trackingDataToSend[oneDoc.id] = {data: oneDoc.data()};
                    }
                  });
                  callback(null, trackingDataToSend);
                })
                .catch(() => callback());
          } else callback(null, {});
        },
        (callback) => {
          db.collection("purchases")
              .doc(userId)
              .get()
              .then((snapPurchases) => {
                const purchases = snapPurchases.data();
                callback(null, purchases);
              })
              .catch(() => callback());
        },
      ],
      (err, res) => {
        const bookmarksDataToSend = res[0] || {};
        const noteDataToSend = res[1] || {};
        const trackingDataToSend = res[2] || [];
        const purchases = res[3];
        const DataToSend = {
          bookmarks: bookmarksDataToSend,
          notes: noteDataToSend,
          tracking: trackingDataToSend,
          purchases: purchases,
        };
        response.send(DataToSend);
        return DataToSend;
      }
  );
});
exports.deleteUserAccount = functions.https.onRequest((request, response) => {
  const db = admin.firestore();
  const profileIds = request.query.profileIds || "[]";
  const userId = request.query.userId;
  if (userId && !isEmpty(JSON.parse(profileIds))) {
    JSON.parse(profileIds).map((oneId) => {
      parallel(
          [
            (callback) => {
              db.collection("bookmarks")
                  .doc(oneId)
                  .delete()
                  .then(() => {
                    callback();
                  })
                  .catch((err) => {
                    console.log({err});
                    callback();
                  });
            },
            (callback) => {
              db.collection("Tracking")
                  .doc(oneId)
                  .delete()
                  .then(() => {
                    callback();
                  })
                  .catch((err) => {
                    console.log({err});
                    callback();
                  });
            },
            (callback) => {
              db.collection("notes")
                  .doc(oneId)
                  .delete()
                  .then(() => {
                    callback();
                  })
                  .catch((err) => {
                    console.log({err});
                    callback();
                  });
            },
            (callback) => {
              if (oneId == userId) {
                db.collection("purchases")
                    .doc(userId)
                    .delete()
                    .then(() => {
                      callback();
                    })
                    .catch(() => {
                      callback();
                    });
              } else callback();
            },
            (callback) => {
              if (oneId == userId) {
                db.collection("tokens")
                    .doc(userId)
                    .delete()
                    .then(() => {
                      callback();
                    })
                    .catch((err) => {
                      console.log("callback error", {err});
                      callback();
                    });
              } else callback();
            },
            (callback) => {
              if (oneId == userId) {
                db.collection("children")
                    .doc(userId)
                    .delete()
                    .then(() => {
                      callback();
                    })
                    .catch((err) => {
                      console.log("callback error", {err});
                      callback();
                    });
              } else return callback();
            },
          ],
          (err, res) => {
            response.send({success: true});
            return {success: true};
          }
      );
    });
  } else {
    response.send({failed: true});
    return {failed: true};
  }
});
