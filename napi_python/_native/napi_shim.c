/**
 * NAPI Shim Library for napi-python
 * 
 * This library provides NAPI symbols that forward to Python implementations
 * via function pointers set at runtime.
 * 
 * Build with:
 *   clang -shared -fPIC -o libnapi_shim.dylib napi_shim.c
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

// NAPI types
typedef struct napi_env__* napi_env;
typedef struct napi_value__* napi_value;
typedef struct napi_ref__* napi_ref;
typedef struct napi_handle_scope__* napi_handle_scope;
typedef struct napi_callback_info__* napi_callback_info;
typedef struct napi_deferred__* napi_deferred;
typedef struct napi_async_work__* napi_async_work;

typedef enum {
    napi_ok,
    napi_invalid_arg,
    napi_object_expected,
    napi_string_expected,
    napi_name_expected,
    napi_function_expected,
    napi_number_expected,
    napi_boolean_expected,
    napi_array_expected,
    napi_generic_failure,
    napi_pending_exception,
    napi_cancelled,
    napi_escape_called_twice,
    napi_handle_scope_mismatch,
    napi_callback_scope_mismatch,
    napi_queue_full,
    napi_closing,
    napi_bigint_expected,
    napi_date_expected,
    napi_arraybuffer_expected,
    napi_detachable_arraybuffer_expected,
    napi_would_deadlock,
    napi_no_external_buffers_allowed,
    napi_cannot_run_js
} napi_status;

typedef enum {
    napi_undefined,
    napi_null,
    napi_boolean,
    napi_number,
    napi_string,
    napi_symbol,
    napi_object,
    napi_function,
    napi_external,
    napi_bigint
} napi_valuetype;

typedef enum {
    napi_int8_array,
    napi_uint8_array,
    napi_uint8_clamped_array,
    napi_int16_array,
    napi_uint16_array,
    napi_int32_array,
    napi_uint32_array,
    napi_float32_array,
    napi_float64_array,
    napi_bigint64_array,
    napi_biguint64_array
} napi_typedarray_type;

typedef enum {
    napi_default = 0,
    napi_writable = 1 << 0,
    napi_enumerable = 1 << 1,
    napi_configurable = 1 << 2,
    napi_static = 1 << 10,
} napi_property_attributes;

typedef napi_value (*napi_callback)(napi_env env, napi_callback_info info);
typedef void (*napi_finalize)(napi_env env, void* finalize_data, void* finalize_hint);

typedef struct {
    const char* error_message;
    void* engine_reserved;
    uint32_t engine_error_code;
    napi_status error_code;
} napi_extended_error_info;

typedef struct {
    const char* utf8name;
    napi_value name;
    napi_callback method;
    napi_callback getter;
    napi_callback setter;
    napi_value value;
    napi_property_attributes attributes;
    void* data;
} napi_property_descriptor;

// Function pointer table - set by Python at runtime
typedef struct {
    napi_status (*get_version)(napi_env env, uint32_t* result);
    napi_status (*get_undefined)(napi_env env, napi_value* result);
    napi_status (*get_null)(napi_env env, napi_value* result);
    napi_status (*get_global)(napi_env env, napi_value* result);
    napi_status (*get_boolean)(napi_env env, bool value, napi_value* result);
    napi_status (*create_int32)(napi_env env, int32_t value, napi_value* result);
    napi_status (*create_uint32)(napi_env env, uint32_t value, napi_value* result);
    napi_status (*create_int64)(napi_env env, int64_t value, napi_value* result);
    napi_status (*create_double)(napi_env env, double value, napi_value* result);
    napi_status (*create_string_utf8)(napi_env env, const char* str, size_t length, napi_value* result);
    napi_status (*get_value_bool)(napi_env env, napi_value value, bool* result);
    napi_status (*get_value_int32)(napi_env env, napi_value value, int32_t* result);
    napi_status (*get_value_uint32)(napi_env env, napi_value value, uint32_t* result);
    napi_status (*get_value_int64)(napi_env env, napi_value value, int64_t* result);
    napi_status (*get_value_double)(napi_env env, napi_value value, double* result);
    napi_status (*get_value_string_utf8)(napi_env env, napi_value value, char* buf, size_t bufsize, size_t* result);
    napi_status (*typeof_)(napi_env env, napi_value value, napi_valuetype* result);
    napi_status (*is_array)(napi_env env, napi_value value, bool* result);
    napi_status (*is_typedarray)(napi_env env, napi_value value, bool* result);
    napi_status (*is_error)(napi_env env, napi_value value, bool* result);
    napi_status (*create_object)(napi_env env, napi_value* result);
    napi_status (*create_array)(napi_env env, napi_value* result);
    napi_status (*get_array_length)(napi_env env, napi_value value, uint32_t* result);
    napi_status (*get_element)(napi_env env, napi_value object, uint32_t index, napi_value* result);
    napi_status (*set_element)(napi_env env, napi_value object, uint32_t index, napi_value value);
    napi_status (*get_property)(napi_env env, napi_value object, napi_value key, napi_value* result);
    napi_status (*set_property)(napi_env env, napi_value object, napi_value key, napi_value value);
    napi_status (*get_named_property)(napi_env env, napi_value object, const char* utf8name, napi_value* result);
    napi_status (*set_named_property)(napi_env env, napi_value object, const char* utf8name, napi_value value);
    napi_status (*get_cb_info)(napi_env env, napi_callback_info cbinfo, size_t* argc, napi_value* argv, napi_value* this_arg, void** data);
    napi_status (*create_function)(napi_env env, const char* utf8name, size_t length, napi_callback cb, void* data, napi_value* result);
    napi_status (*call_function)(napi_env env, napi_value recv, napi_value func, size_t argc, const napi_value* argv, napi_value* result);
    napi_status (*define_class)(napi_env env, const char* utf8name, size_t length, napi_callback constructor, void* data, size_t property_count, const napi_property_descriptor* properties, napi_value* result);
    napi_status (*create_reference)(napi_env env, napi_value value, uint32_t initial_refcount, napi_ref* result);
    napi_status (*delete_reference)(napi_env env, napi_ref ref);
    napi_status (*get_reference_value)(napi_env env, napi_ref ref, napi_value* result);
    napi_status (*throw_)(napi_env env, napi_value error);
    napi_status (*throw_error)(napi_env env, const char* code, const char* msg);
    napi_status (*create_error)(napi_env env, napi_value code, napi_value msg, napi_value* result);
    napi_status (*is_exception_pending)(napi_env env, bool* result);
    napi_status (*get_and_clear_last_exception)(napi_env env, napi_value* result);
    napi_status (*open_handle_scope)(napi_env env, napi_handle_scope* result);
    napi_status (*close_handle_scope)(napi_env env, napi_handle_scope scope);
    napi_status (*coerce_to_string)(napi_env env, napi_value value, napi_value* result);
    napi_status (*get_typedarray_info)(napi_env env, napi_value typedarray, napi_typedarray_type* type, size_t* length, void** data, napi_value* arraybuffer, size_t* byte_offset);
} NapiPythonFunctions;

// Global function table
static NapiPythonFunctions* g_funcs = NULL;

// Function to set the function table from Python
void napi_python_set_functions(NapiPythonFunctions* funcs) {
    g_funcs = funcs;
}

// Helper macro for checking function table
#define CHECK_FUNCS() if (!g_funcs) return napi_generic_failure

// =============================================================================
// NAPI Function Implementations
// =============================================================================

napi_status napi_get_version(napi_env env, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_version) return g_funcs->get_version(env, result);
    *result = 9;
    return napi_ok;
}

napi_status napi_get_undefined(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_undefined) return g_funcs->get_undefined(env, result);
    return napi_generic_failure;
}

napi_status napi_get_null(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_null) return g_funcs->get_null(env, result);
    return napi_generic_failure;
}

napi_status napi_get_global(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_global) return g_funcs->get_global(env, result);
    return napi_generic_failure;
}

napi_status napi_get_boolean(napi_env env, bool value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_boolean) return g_funcs->get_boolean(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_int32(napi_env env, int32_t value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_int32) return g_funcs->create_int32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_uint32(napi_env env, uint32_t value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_uint32) return g_funcs->create_uint32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_int64(napi_env env, int64_t value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_int64) return g_funcs->create_int64(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_double(napi_env env, double value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_double) return g_funcs->create_double(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_string_utf8(napi_env env, const char* str, size_t length, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_string_utf8) return g_funcs->create_string_utf8(env, str, length, result);
    return napi_generic_failure;
}

napi_status napi_get_value_bool(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_bool) return g_funcs->get_value_bool(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_int32(napi_env env, napi_value value, int32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_int32) return g_funcs->get_value_int32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_uint32(napi_env env, napi_value value, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_uint32) return g_funcs->get_value_uint32(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_int64(napi_env env, napi_value value, int64_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_int64) return g_funcs->get_value_int64(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_double(napi_env env, napi_value value, double* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_double) return g_funcs->get_value_double(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_value_string_utf8(napi_env env, napi_value value, char* buf, size_t bufsize, size_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_value_string_utf8) return g_funcs->get_value_string_utf8(env, value, buf, bufsize, result);
    return napi_generic_failure;
}

napi_status napi_typeof(napi_env env, napi_value value, napi_valuetype* result) {
    CHECK_FUNCS();
    if (g_funcs->typeof_) return g_funcs->typeof_(env, value, result);
    return napi_generic_failure;
}

napi_status napi_is_array(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_array) return g_funcs->is_array(env, value, result);
    return napi_generic_failure;
}

napi_status napi_is_typedarray(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_typedarray) return g_funcs->is_typedarray(env, value, result);
    return napi_generic_failure;
}

napi_status napi_is_error(napi_env env, napi_value value, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_error) return g_funcs->is_error(env, value, result);
    return napi_generic_failure;
}

napi_status napi_create_object(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_object) return g_funcs->create_object(env, result);
    return napi_generic_failure;
}

napi_status napi_create_array(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_array) return g_funcs->create_array(env, result);
    return napi_generic_failure;
}

napi_status napi_get_array_length(napi_env env, napi_value value, uint32_t* result) {
    CHECK_FUNCS();
    if (g_funcs->get_array_length) return g_funcs->get_array_length(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_element(napi_env env, napi_value object, uint32_t index, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_element) return g_funcs->get_element(env, object, index, result);
    return napi_generic_failure;
}

napi_status napi_set_element(napi_env env, napi_value object, uint32_t index, napi_value value) {
    CHECK_FUNCS();
    if (g_funcs->set_element) return g_funcs->set_element(env, object, index, value);
    return napi_generic_failure;
}

napi_status napi_get_property(napi_env env, napi_value object, napi_value key, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_property) return g_funcs->get_property(env, object, key, result);
    return napi_generic_failure;
}

napi_status napi_set_property(napi_env env, napi_value object, napi_value key, napi_value value) {
    CHECK_FUNCS();
    if (g_funcs->set_property) return g_funcs->set_property(env, object, key, value);
    return napi_generic_failure;
}

napi_status napi_get_named_property(napi_env env, napi_value object, const char* utf8name, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_named_property) return g_funcs->get_named_property(env, object, utf8name, result);
    return napi_generic_failure;
}

napi_status napi_set_named_property(napi_env env, napi_value object, const char* utf8name, napi_value value) {
    CHECK_FUNCS();
    if (g_funcs->set_named_property) return g_funcs->set_named_property(env, object, utf8name, value);
    return napi_generic_failure;
}

napi_status napi_get_cb_info(napi_env env, napi_callback_info cbinfo, size_t* argc, napi_value* argv, napi_value* this_arg, void** data) {
    CHECK_FUNCS();
    if (g_funcs->get_cb_info) return g_funcs->get_cb_info(env, cbinfo, argc, argv, this_arg, data);
    return napi_generic_failure;
}

napi_status napi_create_function(napi_env env, const char* utf8name, size_t length, napi_callback cb, void* data, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_function) return g_funcs->create_function(env, utf8name, length, cb, data, result);
    return napi_generic_failure;
}

napi_status napi_call_function(napi_env env, napi_value recv, napi_value func, size_t argc, const napi_value* argv, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->call_function) return g_funcs->call_function(env, recv, func, argc, argv, result);
    return napi_generic_failure;
}

napi_status napi_define_class(napi_env env, const char* utf8name, size_t length, napi_callback constructor, void* data, size_t property_count, const napi_property_descriptor* properties, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->define_class) return g_funcs->define_class(env, utf8name, length, constructor, data, property_count, properties, result);
    return napi_generic_failure;
}

napi_status napi_create_reference(napi_env env, napi_value value, uint32_t initial_refcount, napi_ref* result) {
    CHECK_FUNCS();
    if (g_funcs->create_reference) return g_funcs->create_reference(env, value, initial_refcount, result);
    return napi_generic_failure;
}

napi_status napi_delete_reference(napi_env env, napi_ref ref) {
    CHECK_FUNCS();
    if (g_funcs->delete_reference) return g_funcs->delete_reference(env, ref);
    return napi_generic_failure;
}

napi_status napi_get_reference_value(napi_env env, napi_ref ref, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_reference_value) return g_funcs->get_reference_value(env, ref, result);
    return napi_generic_failure;
}

napi_status napi_throw(napi_env env, napi_value error) {
    CHECK_FUNCS();
    if (g_funcs->throw_) return g_funcs->throw_(env, error);
    return napi_generic_failure;
}

napi_status napi_throw_error(napi_env env, const char* code, const char* msg) {
    CHECK_FUNCS();
    if (g_funcs->throw_error) return g_funcs->throw_error(env, code, msg);
    return napi_generic_failure;
}

napi_status napi_create_error(napi_env env, napi_value code, napi_value msg, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->create_error) return g_funcs->create_error(env, code, msg, result);
    return napi_generic_failure;
}

napi_status napi_is_exception_pending(napi_env env, bool* result) {
    CHECK_FUNCS();
    if (g_funcs->is_exception_pending) return g_funcs->is_exception_pending(env, result);
    *result = false;
    return napi_ok;
}

napi_status napi_get_and_clear_last_exception(napi_env env, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->get_and_clear_last_exception) return g_funcs->get_and_clear_last_exception(env, result);
    return napi_generic_failure;
}

napi_status napi_open_handle_scope(napi_env env, napi_handle_scope* result) {
    CHECK_FUNCS();
    if (g_funcs->open_handle_scope) return g_funcs->open_handle_scope(env, result);
    return napi_generic_failure;
}

napi_status napi_close_handle_scope(napi_env env, napi_handle_scope scope) {
    CHECK_FUNCS();
    if (g_funcs->close_handle_scope) return g_funcs->close_handle_scope(env, scope);
    return napi_generic_failure;
}

napi_status napi_coerce_to_string(napi_env env, napi_value value, napi_value* result) {
    CHECK_FUNCS();
    if (g_funcs->coerce_to_string) return g_funcs->coerce_to_string(env, value, result);
    return napi_generic_failure;
}

napi_status napi_get_typedarray_info(napi_env env, napi_value typedarray, napi_typedarray_type* type, size_t* length, void** data, napi_value* arraybuffer, size_t* byte_offset) {
    CHECK_FUNCS();
    if (g_funcs->get_typedarray_info) return g_funcs->get_typedarray_info(env, typedarray, type, length, data, arraybuffer, byte_offset);
    return napi_generic_failure;
}

// Last error info - simple implementation
static napi_extended_error_info g_last_error = {0};

napi_status napi_get_last_error_info(napi_env env, const napi_extended_error_info** result) {
    if (result) *result = &g_last_error;
    return napi_ok;
}
